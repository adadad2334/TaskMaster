"""
Router for task assignment optimization.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, crud
from ..assign import assign_tasks
from ..database import get_db
from ..auth import get_current_active_user

router = APIRouter(
    prefix="/assign",
    tags=["assign"],
    dependencies=[Depends(get_current_active_user)]
)

# Expose the assign_tasks function
assign_tasks = assign_tasks

@router.post("/tasks", response_model=schemas.AutoAssignmentResponse)
def assign_project_tasks(
    assignment_request: schemas.AssignmentRequest,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """
    Автоматически назначает задачи в проекте оптимальным исполнителям.
    
    - **project_id**: ID проекта
    - **optimize_for**: Стратегия оптимизации (balanced, workload, skills, priority)
    """
    project_id = assignment_request.project_id
    optimize_for = assignment_request.optimize_for
    
    project = crud.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Проверяем, что пользователь является участником проекта
    is_member = any(member.id == current_user.id for member in project.members)
    if not is_member:
        raise HTTPException(
            status_code=403,
            detail="You must be a member of the project to assign tasks"
        )
    
    try:
        result = assign_tasks(db, project_id, optimize_for)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e 