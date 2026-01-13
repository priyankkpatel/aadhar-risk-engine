from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health():
    return {
        "status": "active",
        "system": "Aadhaar CIIM Risk Engine",
        "version": "1.0"
    }
