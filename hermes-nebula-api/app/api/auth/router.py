import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError
from app.database import get_db
from app.config import get_settings
from app.models.user import User
from app.api.auth.google import oauth
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def create_access_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


@router.get("/google")
async def google_login(request: Request):
    redirect_uri = f"{settings.next_public_api_url}/auth/google/callback"
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Google authentication failed: {str(e)}")
        
    user_info = token.get("userinfo")
    if not user_info:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to retrieve Google user profile info")

    google_id = user_info["sub"]
    email = user_info["email"]
    display_name = user_info.get("name", email.split("@")[0])
    avatar_url = user_info.get("picture")

    # Chercher l'utilisateur
    stmt = select(User).where(User.google_id == google_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    is_new = False
    if user is None:
        # Vérifier si un user avec cet email existe déjà
        stmt_email = select(User).where(User.email == email)
        result_email = await db.execute(stmt_email)
        user = result_email.scalar_one_or_none()

        if user is None:
            is_new = True
            # Compter s'il s'agit du premier utilisateur créé dans la base de données
            # pour le désigner automatiquement comme superadmin.
            user_count_stmt = select(User)
            user_count_res = await db.execute(user_count_stmt)
            all_users = user_count_res.scalars().all()
            
            # S'il n'y a aucun utilisateur, le premier est superadmin et actif par défaut
            is_first_user = len(all_users) == 0
            
            user = User(
                email=email,
                display_name=display_name,
                google_id=google_id,
                avatar_url=avatar_url,
                is_active=is_first_user,  # Le premier utilisateur est actif de suite
                is_superadmin=is_first_user,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            # Lier le compte Google
            user.google_id = google_id
            if avatar_url:
                user.avatar_url = avatar_url
            await db.commit()
            await db.refresh(user)

    # Récupérer l'origine du frontend Next.js à partir de la config
    frontend_url = settings.next_public_api_url.replace("/api", "")

    # Si c'est un nouvel utilisateur non actif, on le redirige vers /pending
    if not user.is_active:
        return RedirectResponse(url=f"{frontend_url}/pending?email={email}")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return RedirectResponse(
        url=f"{frontend_url}/login?token={access_token}&refresh_token={refresh_token}"
    )


@router.post("/dev-login")
async def dev_login(body: dict, db: AsyncSession = Depends(get_db)):
    """DEV ONLY: génère un JWT pour un email existant (bypass Google OAuth).

    Sécurité : désactivé en production.
    Usage : POST /api/auth/dev-login {"email": "younes@eaumalik.com"}
    """
    if settings.hermes_env == "production":
        raise HTTPException(status_code=403, detail="Dev login disabled in production")

    email = body.get("email", "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email required")

    stmt = select(User).where(User.email == email)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {email} not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User not active")

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "is_active": user.is_active,
            "is_superadmin": user.is_superadmin,
        },
    }


@router.post("/refresh")
async def refresh_session(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    refresh_token = body.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Missing refresh token")
        
    try:
        payload = jwt.decode(refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(str(user.id))

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "timezone": user.timezone,
        "is_active": user.is_active,
        "is_superadmin": user.is_superadmin,
    }
