from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.projects import router as projects_router
from app.api.v1.meetings import router as meetings_router
from app.api.v1.media import router as media_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.scores import router as scores_router
from app.api.v1.datasets import router as datasets_router
from app.api.v1.experiments import router as experiments_router
from app.api.v1.models import router as models_router
from app.api.v1.reports import router as reports_router
from app.api.v1.visual_reports import router as visual_reports_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(projects_router)
api_router.include_router(meetings_router)
api_router.include_router(media_router)
api_router.include_router(jobs_router)
api_router.include_router(scores_router)
api_router.include_router(datasets_router)
api_router.include_router(experiments_router)
api_router.include_router(models_router)
api_router.include_router(reports_router)
api_router.include_router(visual_reports_router)
