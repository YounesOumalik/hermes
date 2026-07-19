"""
hermes-core/api/agents.py — CRUD agents + presets (11 templates Master Prompt §18).

Routes :
  GET    /api/agents                  — liste
  POST   /api/agents                  — create
  GET    /api/agents/{id}            — détail
  PUT    /api/agents/{id}            — update (répare le bug UI actuel)
  DELETE /api/agents/{id}            — delete
  GET    /api/agents/presets         — 11 templates
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from db.models import Agent
from .schemas import AgentCreate, AgentUpdate, AgentOut

logger = logging.getLogger("hermes.core.api.agents")

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _agent_to_out(a: Agent) -> AgentOut:
    return AgentOut(
        id=a.id,
        name=a.name,
        description=a.description,
        system_prompt=a.system_prompt,
        model=a.model,
        temperature=a.temperature / 10.0 if a.temperature else 0.7,
        max_tokens=a.max_tokens,
        tools=a.tools or [],
        enabled=a.enabled,
        is_preset=a.is_preset,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


# 11 presets du Master Prompt §18
PRESETS = [
    {
        "name": "Marketing Strategist",
        "description": "Stratégie marketing globale, positionnement et plans de campagne",
        "system_prompt": "Tu es un stratège marketing senior. Tu analyses le marché, identifies les segments cibles et proposes des plans marketing cohérents (positionnement, message, canaux, KPIs).",
        "tools": ["web_search", "web_fetch"],
        "model": "MiniMax-M2.7",
    },
    {
        "name": "SEO Specialist",
        "description": "Audit SEO, mots-clés, optimisation on-page et technique",
        "system_prompt": "Tu es un expert SEO. Tu effectues des audits techniques, recherches des mots-clés et proposes des optimisations on-page (balises, contenu, structure, maillage interne).",
        "tools": ["web_search", "mcp_filesystem", "web_fetch"],
        "model": "MiniMax-M2.7",
    },
    {
        "name": "Social Media Manager",
        "description": "Création de posts, calendriers éditoriaux et engagement social",
        "system_prompt": "Tu es un social media manager. Tu crées des posts engageants pour les réseaux sociaux, gères les calendriers éditoriaux et adaptes le ton selon les plateformes.",
        "tools": ["web_search", "n8n_webhook"],
        "model": "MiniMax-M2.7",
    },
    {
        "name": "Research Analyst",
        "description": "Recherche longue, synthèse de sources et rapports structurés",
        "system_prompt": "Tu es un analyste de recherche. Tu effectues des recherches approfondies, croises les sources et produis des rapports structurés avec citations.",
        "tools": ["web_search", "web_fetch", "mcp_filesystem"],
        "model": "MiniMax-M3",
    },
    {
        "name": "Developer Agent",
        "description": "Développement web/code, debug et revues de PR",
        "system_prompt": "Tu es un développeur senior full-stack. Tu écris du code propre, documenté, testé. Tu fais des revues de PR rigoureuses et proposes des refactors.",
        "tools": ["mcp_terminal", "mcp_filesystem", "mcp_github"],
        "model": "MiniMax-M3",
    },
    {
        "name": "Data Analyst",
        "description": "Analyse de données, CSV/Excel, génération de rapports",
        "system_prompt": "Tu es un analyste de données. Tu explores des datasets (CSV, Excel), identifies des patterns et produis des rapports avec visualisations.",
        "tools": ["mcp_terminal", "mcp_filesystem", "web_search"],
        "model": "MiniMax-M3",
    },
    {
        "name": "Executive Assistant",
        "description": "Gestion d'agenda, emails, résumés et actions de suivi",
        "system_prompt": "Tu es un assistant exécutif. Tu gères l'agenda, priorises les emails, proposes des actions de suivi et synthétises les informations importantes.",
        "tools": ["n8n_webhook", "web_search"],
        "model": "MiniMax-M2.7",
    },
    {
        "name": "Content Agent",
        "description": "Création de contenu (articles, blog, newsletters)",
        "system_prompt": "Tu es un content writer. Tu écris des articles engageants, structurés, optimisés SEO. Tu adaptes le ton selon la cible (B2B vs B2C, technique vs vulgarisé).",
        "tools": ["web_search", "web_fetch", "mcp_filesystem"],
        "model": "MiniMax-M3",
    },
    {
        "name": "Customer Support",
        "description": "Support client, FAQ, escalade et résolution",
        "system_prompt": "Tu es un agent de support client. Tu réponds avec empathie, résous les problèmes courants et escalades les cas complexes.",
        "tools": ["n8n_webhook"],
        "model": "MiniMax-M2.7-highspeed",
    },
    {
        "name": "Finance Assistant",
        "description": "Analyse financière, budgets, rapports et prévisions",
        "system_prompt": "Tu es un assistant financier. Tu analyses des budgets, produis des rapports financiers et proposes des optimisations de coûts.",
        "tools": ["mcp_filesystem", "mcp_terminal"],
        "model": "MiniMax-M3",
    },
    {
        "name": "Custom Agent",
        "description": "Agent personnalisé (configurable à la création)",
        "system_prompt": "Tu es un assistant IA polyvalent. Adapte ton comportement selon les instructions spécifiques fournies par l'utilisateur.",
        "tools": [],
        "model": "MiniMax-M2.7",
    },
]


@router.get("/presets", response_model=List[AgentOut])
async def list_presets():
    """Retourne les 11 templates d'agents du Master Prompt §18 (non persistés)."""
    return [
        AgentOut(
            id=0,
            name=p["name"],
            description=p["description"],
            system_prompt=p["system_prompt"],
            model=p["model"],
            temperature=0.7,
            max_tokens=2000,
            tools=p["tools"],
            enabled=True,
            is_preset=True,
            created_at=None,  # type: ignore
            updated_at=None,  # type: ignore
        )
        for p in PRESETS
    ]


@router.get("", response_model=List[AgentOut])
async def list_agents(
    enabled_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Liste tous les agents."""
    stmt = select(Agent).order_by(Agent.is_preset.desc(), Agent.name)
    if enabled_only:
        stmt = stmt.where(Agent.enabled == True)  # noqa: E712
    result = await db.execute(stmt)
    return [_agent_to_out(a) for a in result.scalars()]


@router.post("", response_model=AgentOut, status_code=201)
async def create_agent(
    payload: AgentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Crée un nouvel agent."""
    # Vérifier unicité du nom
    existing = await db.execute(select(Agent).where(Agent.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Agent '{payload.name}' existe déjà")

    # Stocker temperature * 10 pour éviter les floats (cf. model definition)
    agent = Agent(
        name=payload.name,
        description=payload.description,
        system_prompt=payload.system_prompt,
        model=payload.model,
        temperature=int(payload.temperature * 10),
        max_tokens=payload.max_tokens,
        tools=payload.tools,
        enabled=payload.enabled,
        is_preset=False,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _agent_to_out(agent)


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Détail d'un agent."""
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent introuvable")
    return _agent_to_out(agent)


@router.put("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: int,
    payload: AgentUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update agent (répare le bug UI actuel qui attendait ce endpoint)."""
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent introuvable")

    # Update fields
    agent.description = payload.description
    agent.system_prompt = payload.system_prompt
    agent.model = payload.model
    agent.temperature = int(payload.temperature * 10)
    agent.max_tokens = payload.max_tokens
    agent.tools = payload.tools
    agent.enabled = payload.enabled

    await db.commit()
    await db.refresh(agent)
    return _agent_to_out(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Supprime un agent (interdit pour les presets)."""
    agent = await db.get(Agent, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent introuvable")
    if agent.is_preset:
        raise HTTPException(status_code=403, detail="Impossible de supprimer un preset")

    await db.delete(agent)
    await db.commit()
    return None