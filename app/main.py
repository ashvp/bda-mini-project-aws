import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import engine, Base, SessionLocal
from app.models.user import User
from app.services.auth import hash_password
from app.routers import auth_router, maintenance_router, admin_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("property_maintenance")

settings = get_settings()


def seed_admin_user():
    """Pre-seed the admin user from .env credentials if not already present."""
    db = SessionLocal()
    try:
        admin_username = settings.ADMIN_USERNAME.strip()
        existing_admin = db.query(User).filter(User.username == admin_username).first()

        if not existing_admin:
            logger.info(f"Admin user '{admin_username}' not found. Seeding initial admin from .env...")
            admin_user = User(
                username=admin_username,
                pw_hashed=hash_password(settings.ADMIN_PASSWORD),
                houseid=None,
                isAdmin=True
            )
            db.add(admin_user)
            db.commit()
            logger.info(f"Admin user '{admin_username}' successfully seeded.")
        else:
            # Ensure the pre-seeded admin user retains admin privileges
            if not existing_admin.isAdmin:
                existing_admin.isAdmin = True
                db.commit()
            logger.info(f"Admin user '{admin_username}' verified.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error during admin user seeding: {e}", exc_info=True)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")

    # Seed Admin User
    seed_admin_user()

    # Create local upload dir if mock is enabled
    if settings.USE_LOCAL_S3_MOCK or not (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY):
        os.makedirs(settings.LOCAL_UPLOAD_DIR, exist_ok=True)

    yield
    # --- Shutdown ---
    logger.info("Application shutting down...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="FastAPI Backend for Property Maintenance Tracking with unified authentication, AWS S3 image storage, and admin assignment workflow.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Serve static web frontend assets
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve local uploads for image viewing when running locally or with mock S3
os.makedirs(settings.LOCAL_UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.LOCAL_UPLOAD_DIR), name="uploads")

# Include API Routers
app.include_router(auth_router)
app.include_router(maintenance_router)
app.include_router(admin_router)


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Custom HTTP exception handler:
    Serves the cool, animated 404 cyber-security defense page for browsers,
    while returning JSON for programmatic API clients.
    """
    if exc.status_code == 404:
        accept = request.headers.get("accept", "")
        # If API client strictly requested JSON
        if "application/json" in accept and "text/html" not in accept:
            return JSONResponse(
                status_code=404,
                content={"detail": "Sector not found. Error 404."}
            )
        # For browsers / nosy visitors, serve the animated 404 page
        not_found_file = os.path.join("static", "404.html")
        if os.path.exists(not_found_file):
            return FileResponse(not_found_file, status_code=404)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/", tags=["General"], summary="Frontend Portal & Status")
def root():
    index_file = os.path.join("static", "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "healthy"
    }


@app.get("/404", tags=["General"], summary="Preview 404 Page")
def preview_404():
    return FileResponse(os.path.join("static", "404.html"), status_code=404)


@app.get("/api/info", tags=["General"], summary="API Meta Info")
def api_info():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "status": "healthy"
    }


@app.get("/health", tags=["General"], summary="Health Check")
def health_check():
    return {
        "status": "UP",
        "database": "connected",
        "storage_mode": "mock_s3" if settings.USE_LOCAL_S3_MOCK else "aws_s3"
    }


