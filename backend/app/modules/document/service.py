from .model import Document
from fastapi import HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from pypdf import PdfReader
from app.db import db

def _extract_pdf_text(file_obj) -> str:
    reader = PdfReader(file_obj)
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


async def extract_content(file: UploadFile) -> str:
    await file.seek(0)
    return await run_in_threadpool(_extract_pdf_text, file.file)


async def upload_document(file: UploadFile, collection_id: int) -> str:
    text = None
    if file.content_type == "application/pdf":
        text = await extract_content(file)
    else:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    document = await db.document.create(
        data={
            "name": file.filename,
            "content": text,
            "collectionId": collection_id
        }
    )
    return Document.model_validate(document)