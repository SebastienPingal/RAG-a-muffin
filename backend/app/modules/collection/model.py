from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.document.model import Document


class Collection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    userId: int
    documents: Optional[list[Document]] = []
    createdAt: datetime
    updatedAt: datetime

class CollectionCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    userId: int