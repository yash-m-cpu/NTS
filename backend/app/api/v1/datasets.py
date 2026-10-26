from fastapi import APIRouter
router = APIRouter(prefix="/datasets", tags=["datasets"])

@router.get("")
async def list_datasets():
    return {"data": [], "pagination": {"limit": 20, "offset": 0, "total": 0}}
