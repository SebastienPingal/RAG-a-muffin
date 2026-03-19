from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class User(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: Optional[str] = None
    googleId: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime

class UserCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: str
    name: str = None

class UserUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = None