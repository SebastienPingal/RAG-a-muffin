from datetime import datetime
from pydantic import BaseModel, ConfigDict

class Document(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    content: str
    collectionId: int
    createdAt: datetime
    updatedAt: datetime


class DocumentCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    content: str
    collectionId: int