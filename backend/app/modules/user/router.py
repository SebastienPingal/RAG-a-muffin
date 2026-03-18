from fastapi import APIRouter, HTTPException

from app.modules.user.model import User, UserCreate
from app.modules.user.service import create, get_all, get_by_id

router = APIRouter()


@router.get("", response_model=list[User], description="Get all users")
async def get_all_users():
    return await get_all()


@router.get("/{user_id}", response_model=User, description="Get user by id")
async def get_user(user_id: int):
    user = await get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("", response_model=User, description="Create user")
async def create_user(user: UserCreate):
    return await create(email=user.email, name=user.name)