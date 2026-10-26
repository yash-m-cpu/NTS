from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_org, get_db
from app.models.projects import Project
from app.models.users import User
from app.schemas.projects import ProjectCreate, ProjectResponse, ProjectUpdate
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/projects", tags=["projects"])

# Add from_attributes to schema dynamically or use model_validate
def dump_project(project):
    return ProjectResponse.model_validate(project, from_attributes=True).model_dump()

@router.get("", response_model=dict)
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org),
    status: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    query = select(Project).where(Project.deleted_at.is_(None))
    if status:
        query = query.where(Project.status == status)
        
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    projects = result.scalars().all()
    
    count_query = select(func.count()).select_from(Project).where(Project.deleted_at.is_(None))
    if status:
        count_query = count_query.where(Project.status == status)
    
    total = await db.scalar(count_query)
    
    return {
        "data": [dump_project(p) for p in projects],
        "pagination": {
            "limit": limit,
            "offset": offset,
            "total": total or 0,
            "next_cursor": None
        }
    }

@router.post("", response_model=dict, status_code=201)
async def create_project(
    project_in: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    existing = await db.scalar(select(Project).where(Project.name == project_in.name, Project.organization_id == UUID(org_id), Project.deleted_at.is_(None)))
    if existing:
        raise HTTPException(status_code=409, detail="Project with this name already exists")
        
    project = Project(
        organization_id=UUID(org_id),
        name=project_in.name,
        description=project_in.description,
        created_by_user_id=current_user.id
    )
    db.add(project)
    
    from sqlalchemy.exc import IntegrityError
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A project with this name already exists in your organization.")
        
    if not project.id:
        from uuid import uuid4
        project.id = uuid4()
        from datetime import datetime
        project.created_at = datetime.now()
        project.updated_at = datetime.now()
        project.status = "active"
    
    return {"data": dump_project(project)}

@router.get("/{id}", response_model=dict)
async def get_project(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    project = await db.scalar(select(Project).where(Project.id == id, Project.deleted_at.is_(None)))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"data": dump_project(project)}

@router.patch("/{id}", response_model=dict)
async def update_project(
    id: UUID,
    project_in: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    project = await db.scalar(select(Project).where(Project.id == id, Project.deleted_at.is_(None)))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    if project_in.name is not None:
        project.name = project_in.name
    if project_in.description is not None:
        project.description = project_in.description
    if project_in.status is not None:
        project.status = project_in.status
        
    from sqlalchemy.exc import IntegrityError
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="A project with this name already exists in your organization.")
        
    return {"data": dump_project(project)}

@router.delete("/{id}", status_code=204)
async def delete_project(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_id: str = Depends(get_current_org)
):
    project = await db.scalar(select(Project).where(Project.id == id, Project.deleted_at.is_(None)))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    from datetime import datetime
    project.deleted_at = datetime.now()
    await db.commit()
