import uuid
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.config import get_settings
from app.api.deps import get_current_user
from app.models.user import User
from app.models.audit import UserQuota
from app.models.workspace import WorkspaceMember
from app.models.message import Attachment, AttachmentType, Conversation

router = APIRouter(prefix="/files", tags=["files"])
settings = get_settings()


@router.post("/upload")
async def upload_file_to_conversation(
    conversation_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # 1. Vérifier la conversation et l'appartenance
    stmt_conv = select(Conversation).where(Conversation.id == conversation_id)
    res_conv = await db.execute(stmt_conv)
    conv = res_conv.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    if conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Conversation access denied")

    # 2. Vérifier les quotas disques
    stmt_quota = select(UserQuota).where(UserQuota.user_id == current_user.id)
    res_quota = await db.execute(stmt_quota)
    quota = res_quota.scalar_one_or_none()

    if not quota and not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Upload denied. No disk quota record.")

    # Lire le contenu pour connaître la taille
    contents = await file.read()
    file_size = len(contents)

    if not current_user.is_superadmin:
        remaining_disk = quota.max_disk_bytes - quota.used_disk_bytes
        if file_size > remaining_disk:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Disk quota exceeded. Delete some files or contact your administrator."
            )

    # 3. Écrire le fichier dans le dossier d'uploads
    os.makedirs(settings.upload_dir, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.upload_dir, unique_filename)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Déterminer le type d'attachement à partir du mime type
    mime = file.content_type or ""
    att_type = AttachmentType.file.value
    if mime.startswith("image/"):
        att_type = AttachmentType.image.value
    elif mime.startswith("video/"):
        att_type = AttachmentType.video.value
    elif mime.startswith("audio/"):
        att_type = AttachmentType.audio.value

    # 4. Créer l'enregistrement Attachment en DB
    # Note: message_id sera associé plus tard au moment de l'envoi du message,
    # pour l'instant il reste nul (ou associé à une valeur par défaut).
    # On modifie le constructeur pour accepter message_id optionnel.
    attachment = Attachment(
        message_id=uuid.UUID("00000000-0000-0000-0000-000000000000"), # ID temporaire
        conversation_id=conversation_id,
        type=att_type,
        storage_path=file_path,
        original_filename=file.filename or "unknown",
        size_bytes=file_size,
        mime_type=mime
    )
    db.add(attachment)

    # Mettre à jour le quota disque
    if quota:
        quota.used_disk_bytes += file_size
        
    await db.commit()
    await db.refresh(attachment)

    return {
        "id": str(attachment.id),
        "filename": attachment.original_filename,
        "size_bytes": attachment.size_bytes,
        "mime_type": attachment.mime_type,
        "type": attachment.type,
    }


@router.get("/{id}")
async def download_file(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Attachment).where(Attachment.id == id)
    res = await db.execute(stmt)
    attachment = res.scalar_one_or_none()

    if not attachment:
        raise HTTPException(status_code=404, detail="File not found")

    # Vérifier l'appartenance à la conversation
    stmt_conv = select(Conversation).where(Conversation.id == attachment.conversation_id)
    res_conv = await db.execute(stmt_conv)
    conv = res_conv.scalar_one_or_none()

    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="File access denied")

    if not os.path.exists(attachment.storage_path):
        raise HTTPException(status_code=404, detail="File physical storage not found")

    return FileResponse(
        path=attachment.storage_path,
        filename=attachment.original_filename,
        media_type=attachment.mime_type
    )
