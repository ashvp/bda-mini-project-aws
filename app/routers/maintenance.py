from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.maintenance import Maintenance
from app.schemas.maintenance import MaintenanceResponse
from app.services.s3 import upload_maintenance_image
from app.dependencies import get_current_user

router = APIRouter(prefix="/maintenance", tags=["Maintenance (Resident)"])


@router.post(
    "",
    response_model=MaintenanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new maintenance request with photo"
)
async def create_maintenance_request(
    problem_category: str = Form(..., min_length=2, max_length=100, description="e.g., Water Leakage, AC Not Working, Electrical"),
    details: str = Form(..., min_length=5, description="Details explaining the issue"),
    image: UploadFile = File(..., description="Photo of the issue (.jpg, .png, .webp)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Allows an authenticated resident to submit a maintenance request:
    - Validates and uploads the photo to AWS S3 (or mock).
    - Automatically links the resident's house and userid.
    - Saves ticket in database with unassigned status.
    """
    if not current_user.houseid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The current user is not associated with any house. Only registered residents can submit maintenance requests."
        )

    # Upload photo to S3 / Storage
    image_url = await upload_maintenance_image(image)

    new_ticket = Maintenance(
        houseid=current_user.houseid,
        userid=current_user.userid,
        problem_category=problem_category.strip(),
        details=details.strip(),
        image_url=image_url,
        isAssignedTo=None
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return new_ticket


@router.get(
    "/my",
    response_model=List[MaintenanceResponse],
    summary="View all maintenance requests submitted by current user"
)
def get_my_maintenance_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all maintenance requests filed by the logged-in resident."""
    tickets = (
        db.query(Maintenance)
        .filter(Maintenance.userid == current_user.userid)
        .order_by(Maintenance.maintanance_id.desc())
        .all()
    )
    return tickets


@router.get(
    "/{maintanance_id}",
    response_model=MaintenanceResponse,
    summary="Get details of a specific maintenance request"
)
def get_maintenance_request_by_id(
    maintanance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific maintenance ticket.
    Residents can only view their own tickets; admins can view any ticket.
    """
    ticket = db.query(Maintenance).filter(Maintenance.maintanance_id == maintanance_id).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance request #{maintanance_id} not found."
        )

    # Check permission: owner or admin
    if not current_user.isAdmin and ticket.userid != current_user.userid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this maintenance request."
        )

    return ticket
