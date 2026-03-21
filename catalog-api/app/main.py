"""FastAPI application entry point with startup/shutdown lifecycle."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.config import get_settings
from app.database import DatabaseManager
from app.itsm_reader import ITSMReader
from app.models.asset import Base, CatalogAsset
from app.models.user_credential import UserCredential
from app.routers import assets, ai_lab, mcp, auth
from app.services.auth_service import hash_password
from seed.seed_assets import seed_catalog_assets

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def setup_postgres_rbac(pool) -> None:
    """Create platform_admin role and admin PostgreSQL user for direct DB access."""
    statements = [
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'platform_admin') THEN CREATE ROLE platform_admin; END IF; END $$",
        "GRANT USAGE ON SCHEMA analytics TO platform_admin",
        "GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO platform_admin",
        "GRANT USAGE ON SCHEMA raw TO platform_admin",
        "GRANT SELECT ON ALL TABLES IN SCHEMA raw TO platform_admin",
        "DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin') THEN CREATE USER admin WITH PASSWORD 'admin'; END IF; END $$",
        "GRANT platform_admin TO admin",
    ]
    async with pool.acquire() as conn:
        for stmt in statements:
            try:
                await conn.execute(stmt)
            except Exception as e:
                logger.warning(f"RBAC setup statement skipped: {e}")
    logger.info("PostgreSQL RBAC setup complete")


async def seed_admin_user(session_factory) -> None:
    """Ensure the admin catalog user exists in user_credentials."""
    async with session_factory() as session:
        result = await session.execute(
            select(UserCredential).where(UserCredential.email == "admin")
        )
        if not result.scalar_one_or_none():
            session.add(UserCredential(
                email="admin",
                password_hash=hash_password("admin"),
                is_admin=True,
            ))
            await session.commit()
            logger.info("Admin user created")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle handler."""
    try:
        logger.info("Starting up...")

        await DatabaseManager.initialize()
        logger.info("Database initialized")

        engine = DatabaseManager.get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

        await ITSMReader.initialize()
        logger.info("ITSM reader initialized")

        session_factory = DatabaseManager.get_session_factory()

        # Seed catalog assets
        async with session_factory() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM catalog_assets"))
            count = result.scalar()
            if count == 0:
                logger.info("Seeding catalog assets...")
                await seed_catalog_assets(session)
            else:
                logger.info(f"Catalog already seeded ({count} assets)")

        # Seed admin catalog user
        await seed_admin_user(session_factory)

        # Set up PostgreSQL RBAC roles
        await setup_postgres_rbac(ITSMReader.get_pool())

        logger.info("Startup complete")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    try:
        logger.info("Shutting down...")
        await ITSMReader.close()
        await DatabaseManager.close()
        logger.info("Shutdown complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


app = FastAPI(
    title="Catalog API",
    description="AI-ready Data Catalog with Claude integration",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8001",
        "http://localhost:8002",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(assets.router)
app.include_router(ai_lab.router)
app.include_router(mcp.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "catalog-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
