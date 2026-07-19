import asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from app.workers.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.job import Job, JobRun, JobRunStatus
from app.models.agent import Agent
from app.models.message import Conversation, Message, MessageRole
from app.services.llm_router import stream_chat
from app.services.quota_checker import check_token_budget, deduct_tokens


async def execute_scheduled_job(job_id_str: str):
    job_uuid = uuid.UUID(job_id_str)
    
    async with AsyncSessionLocal() as db:
        # 1. Charger le job, l'agent et le modèle
        stmt = select(Job).where(Job.id == job_uuid)
        res = await db.execute(stmt)
        job = res.scalar_one_or_none()
        
        if not job or job.status != "active":
            return
            
        # Créer le log d'exécution du JobRun
        run = JobRun(
            job_id=job.id,
            started_at=datetime.now(timezone.utc),
            status=JobRunStatus.running.value
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)

        try:
            # Charger l'agent
            stmt_agent = select(Agent).where(Agent.id == job.agent_id)
            res_agent = await db.execute(stmt_agent)
            agent = res_agent.scalar_one_or_none()
            
            if not agent:
                raise Exception("Assigned agent not found")

            # 2. Créer une nouvelle conversation pour cette exécution de job
            conversation = Conversation(
                agent_id=agent.id,
                user_id=job.created_by,
                title=f"Scheduled Job Execution: {job.name}"
            )
            db.add(conversation)
            await db.commit()
            await db.refresh(conversation)

            # 3. Enregistrer le message de déclenchement (l'invite du Job)
            trigger_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.user.value,
                content=job.prompt
            )
            db.add(trigger_msg)
            await db.commit()

            # 4. Appeler le LLM et collecter la réponse complète
            model_id = str(agent.model_config_id) if agent.model_config_id else None
            messages = [
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": job.prompt}
            ]

            full_response = ""
            async for chunk in stream_chat(
                model_config_id=model_id,
                messages=messages,
                temperature=0.7
            ):
                if chunk == "[DONE]":
                    break
                full_response += chunk

            # 5. Enregistrer le message de réponse de l'agent
            response_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.assistant.value,
                content=full_response
            )
            db.add(response_msg)

            # Déduire les tokens d'utilisation
            tokens_used = int((len(job.prompt) + len(full_response)) / 4)
            await deduct_tokens(db, job.created_by, tokens_used)

            # Mettre à jour le log d'exécution
            run.status = JobRunStatus.success.value
            run.finished_at = datetime.now(timezone.utc)
            run.result_message_id = response_msg.id
            
        except Exception as e:
            # Enregistrer l'erreur dans le log
            run.status = JobRunStatus.failed.value
            run.finished_at = datetime.now(timezone.utc)
            run.error = str(e)
            
        await db.commit()


@celery_app.task(name="app.workers.tasks.run_scheduled_job_task")
def run_scheduled_job_task(job_id_str: str):
    """Tâche Celery synchrone enveloppant l'exécution asynchrone."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Si une boucle tourne déjà (rare en celery worker standard)
        future = asyncio.run_coroutine_threadsafe(execute_scheduled_job(job_id_str), loop)
        return future.result()
    else:
        return asyncio.run(execute_scheduled_job(job_id_str))
