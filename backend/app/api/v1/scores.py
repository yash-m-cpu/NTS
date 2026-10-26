from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user, get_current_org
from app.models.scores import NtsScore, ModelPrediction
from app.models.users import User

router = APIRouter(prefix="/scores", tags=["scores"])

@router.get("/{id}", response_model=dict)
async def get_score(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    score = await db.scalar(select(NtsScore).where(NtsScore.id == id))
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    
    return {
        "data": {
            "id": str(score.id),
            "nts_score": float(score.nts_score),
            "component_scores": score.component_scores,
            "confidence_interval_low": float(score.confidence_interval_low) if score.confidence_interval_low else None,
            "confidence_interval_high": float(score.confidence_interval_high) if score.confidence_interval_high else None,
        }
    }
