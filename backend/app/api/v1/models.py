from fastapi import APIRouter
router = APIRouter(prefix="/models", tags=["models"])

@router.get("")
async def list_models():
    return {"data": [], "pagination": {"limit": 20, "offset": 0, "total": 0}}
