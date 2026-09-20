from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.house import House
from app.schemas.auth import RegisterRequest, Token
from app.schemas.user import UserResponse
from app.services.auth import hash_password, verify_password, create_access_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new resident user"
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new resident user.
    - Creates or links the house based on apartment_block_num (case-insensitive) and house_num.
    - Checks for unique username.
    - Securely hashes password.
    - Sets isAdmin to False.
    """
    clean_username = payload.username.strip()
    clean_block = payload.apartment_block_num.strip()
    clean_house = payload.house_num.strip()

    # Check if username already exists
    existing_user = db.query(User).filter(User.username == clean_username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{clean_username}' is already taken."
        )

    # Find or create the house (case-insensitive apartment block matching)
    house = db.query(House).filter(
        func.lower(House.apartment_block_num) == clean_block.lower(),
        func.lower(House.house_num) == clean_house.lower()
    ).first()

    if not house:
        house = House(
            apartment_block_num=clean_block,
            house_num=clean_house
        )
        db.add(house)
        db.flush()  # Populates house.houseid

    # Create new user
    new_user = User(
        username=clean_username,
        pw_hashed=hash_password(payload.password),
        houseid=house.houseid,
        isAdmin=False
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@router.post(
    "/login",
    response_model=Token,
    summary="Unified Login for Residents and Administrators"
)
async def login(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Unified login endpoint for both regular users and admins.
    Supports both JSON payloads (`{"username": "...", "password": "..."}`)
    and Form data (for Swagger UI 'Authorize' button).
    """
    content_type = request.headers.get("content-type", "")

    username = ""
    password = ""

    if "application/json" in content_type:
        body = await request.json()
        username = body.get("username", "")
        password = body.get("password", "")
    else:
        form = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username and password are required."
        )

    user = db.query(User).filter(User.username == username.strip()).first()
    if not user or not verify_password(password, user.pw_hashed):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": user.userid,
            "is_admin": user.isAdmin
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile"
)
def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Returns the details of the currently authenticated user."""
    return current_user
