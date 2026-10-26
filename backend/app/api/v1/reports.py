from fastapi import APIRouter
router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/{id}")
async def get_report(id: str):
    return {"data": {"id": id, "sections": []}}
