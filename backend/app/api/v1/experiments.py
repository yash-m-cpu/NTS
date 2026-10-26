from fastapi import APIRouter
router = APIRouter(prefix="/experiments", tags=["experiments"])

@router.get("")
async def list_experiments():
    return {"data": [], "pagination": {"limit": 20, "offset": 0, "total": 0}}
