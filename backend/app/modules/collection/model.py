from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.modules.document.model import Document


class Collection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    userId: int
    documents: Optional[list[Document]] = Field(default_factory=list)
    createdAt: datetime
    updatedAt: datetime

class CollectionCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    userId: int
