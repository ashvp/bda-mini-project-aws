from app.routers.auth import router as auth_router
from app.routers.maintenance import router as maintenance_router
from app.routers.admin import router as admin_router

__all__ = ["auth_router", "maintenance_router", "admin_router"]
