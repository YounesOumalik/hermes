"""Seed initial AgentAI : ModelConfigs, Tools de base, SuperAdmin promotion.

Usage (dans le container agentai-api) :
    python scripts/seed.py
"""
import asyncio
import os
import sys
from pathlib import Path

# Allow running as standalone script: seed.py is in /app/scripts/, app/ is at /app/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
# Also try WORKDIR fallback
if "/app/app" not in sys.path:
    sys.path.insert(0, "/app")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.config import get_settings
from app.models.model_config import ModelConfig, ModelProvider
from app.models.tool import Tool, CostTier
from app.models.user import User
from app.models.audit import UserQuota

settings = get_settings()

DEFAULT_MODELS = [
    # (provider, model_name, display_name, context_window, in_price, out_price, is_default)
    ("minimax", "MiniMax-M2.7", "MiniMax M2.7", 128000, 0.21, 0.63, True),
    ("opencode_zen", "opencode-zen", "OpenCode Zen", 200000, 0.0, 0.0, False),
    ("openai", "gpt-4o-mini", "GPT-4o Mini", 128000, 0.15, 0.60, False),
]

DEFAULT_TOOLS = [
    # (name, slug, description, icon_name, category, cost_tier)
    ("Web Search", "web_search", "Recherche web temps réel (Tavily/Brave)", "search", "research", CostTier.low),
    ("Web Scraping", "web_scraping", "Extraire contenu d'une page web", "link", "research", CostTier.low),
    ("Code Interpreter", "code_interpreter", "Exécuter du code Python en sandbox", "code", "dev", CostTier.medium),
    ("Image Generation", "image_gen", "Générer des images via DALL-E/Stable Diffusion", "image", "creative", CostTier.high),
    ("Calculator", "calculator", "Calculs mathématiques précis (sympy)", "calculator", "utility", CostTier.low),
    ("File Reader", "file_reader", "Lire PDF, DOCX, TXT uploadés", "file-text", "utility", CostTier.low),
]


async def seed():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        # ── 1. ModelConfigs ──
        for provider, model_name, display_name, ctx, in_p, out_p, is_default in DEFAULT_MODELS:
            stmt = select(ModelConfig).where(ModelConfig.model_name == model_name)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                continue
            db.add(ModelConfig(
                provider=ModelProvider(provider),
                model_name=model_name,
                display_name=display_name,
                context_window=ctx,
                input_price_per_1m=in_p,
                output_price_per_1m=out_p,
                capabilities=["text", "streaming"],
                enabled=True,
                is_default=is_default,
            ))
            print(f"  + ModelConfig {model_name}")
        await db.commit()

        # ── 2. Tools ──
        for name, slug, desc, icon, category, tier in DEFAULT_TOOLS:
            stmt = select(Tool).where(Tool.slug == slug)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                continue
            db.add(Tool(
                name=name, slug=slug, description=desc,
                icon_name=icon, category=category, cost_tier=tier,
                is_builtin=True, enabled_globally=True,
            ))
            print(f"  + Tool {slug}")
        await db.commit()

        # ── 3. SuperAdmin promotion ──
        admin_email = settings.superadmin_email or os.getenv("SUPERADMIN_EMAIL", "")
        if admin_email:
            stmt = select(User).where(User.email == admin_email)
            admin = (await db.execute(stmt)).scalar_one_or_none()
            if admin:
                if not admin.is_superadmin or not admin.is_active:
                    admin.is_superadmin = True
                    admin.is_active = True
                    await db.commit()
                    print(f"  ✅ SuperAdmin promoted: {admin_email}")
                else:
                    print(f"  ⏭️  SuperAdmin déjà OK: {admin_email}")
                # Quota par défaut si manquant
                qstmt = select(UserQuota).where(UserQuota.user_id == admin.id)
                if not (await db.execute(qstmt)).scalar_one_or_none():
                    db.add(UserQuota(user_id=admin.id, updated_by_admin_id=admin.id))
                    await db.commit()
                    print(f"  + UserQuota créé pour {admin_email}")
            else:
                print(f"  ⚠️  {admin_email} pas encore créé — sera promu auto à la 1ère connexion Google")
        else:
            print("  ℹ️  SUPERADMIN_EMAIL non défini dans .env")

    await engine.dispose()
    print("\n✅ Seed terminé avec succès")


if __name__ == "__main__":
    asyncio.run(seed())