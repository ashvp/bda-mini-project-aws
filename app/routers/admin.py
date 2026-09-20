from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.house import House
from app.models.maintenance import Maintenance
from app.schemas.maintenance import MaintenanceResponse, MaintenanceAssign
from app.schemas.user import UserResponse
from app.schemas.house import HouseResponse
from app.dependencies import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin (Management & Assignment)"])


@router.get(
    "/maintenance",
    response_model=List[MaintenanceResponse],
    summary="Oversee all maintenance requests with optional filters"
)
def get_all_maintenance_requests(
    is_assigned: Optional[bool] = Query(None, description="Filter by assignment status: True for assigned, False for unassigned"),
    problem_category: Optional[str] = Query(None, description="Filter by problem category"),
    houseid: Optional[int] = Query(None, description="Filter by specific house ID"),
    block: Optional[str] = Query(None, description="Filter by apartment block name (case-insensitive)"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Allows administrator to oversee and monitor all reported property maintenance issues.
    Supports filtering by assignment status, category, house ID, and block name (case-insensitive).
    """
    query = db.query(Maintenance)

    if is_assigned is True:
        query = query.filter(Maintenance.isAssignedTo.isnot(None))
    elif is_assigned is False:
        query = query.filter(Maintenance.isAssignedTo.is_(None))

    if problem_category:
        query = query.filter(Maintenance.problem_category.ilike(f"%{problem_category.strip()}%"))

    if houseid is not None:
        query = query.filter(Maintenance.houseid == houseid)

    if block:
        query = query.join(Maintenance.house).filter(
            func.lower(House.apartment_block_num) == block.strip().lower()
        )

    tickets = query.order_by(Maintenance.maintanance_id.desc()).all()
    return tickets


@router.patch(
    "/maintenance/{maintanance_id}/assign",
    response_model=MaintenanceResponse,
    summary="Assign a worker/technician to a maintenance ticket"
)
def assign_maintenance_ticket(
    maintanance_id: int,
    payload: MaintenanceAssign,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Allows administrator to assign a person or contractor to work on the reported problem.
    Updates the `isAssignedTo` field in the database.
    """
    ticket = db.query(Maintenance).filter(Maintenance.maintanance_id == maintanance_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance ticket #{maintanance_id} not found."
        )

    ticket.isAssignedTo = payload.isAssignedTo.strip()
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all registered residents and admins"
)
def list_users(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all users in the system."""
    return db.query(User).order_by(User.userid.asc()).all()


@router.get(
    "/houses",
    response_model=List[HouseResponse],
    summary="List all registered property houses and apartment blocks"
)
def list_houses(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """List all registered houses."""
    return db.query(House).order_by(House.houseid.asc()).all()


@router.get(
    "/stats",
    response_model=Dict[str, Any],
    summary="Overview statistics of maintenance issues and property status"
)
def get_dashboard_stats(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Returns summarized stats for admin dashboard."""
    total_tickets = db.query(Maintenance).count()
    assigned_tickets = db.query(Maintenance).filter(Maintenance.isAssignedTo.isnot(None)).count()
    unassigned_tickets = db.query(Maintenance).filter(Maintenance.isAssignedTo.is_(None)).count()
    total_houses = db.query(House).count()
    total_residents = db.query(User).filter(User.isAdmin.is_(False)).count()

    return {
        "total_maintenance_requests": total_tickets,
        "assigned_requests": assigned_tickets,
        "unassigned_requests": unassigned_tickets,
        "total_houses": total_houses,
        "total_residents": total_residents,
    }
