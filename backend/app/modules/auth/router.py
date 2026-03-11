from fastapi import APIRouter

router = APIRouter()

@router.post("/google")
def google_login():
    return {"message": "Login successful"}