from __future__ import annotations

from fastapi import APIRouter, Depends
from app.db.models import User
from app.schemas.auth import UserResponse
from app.core.security import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Return current user's profile."""
    return current_user
