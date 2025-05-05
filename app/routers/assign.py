from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas, auth, assign
from ..database import get_db

router = APIRouter(
    prefix="/assign",
    tags=["assign"],
    responses={404: {"description": "Not found"}},
)

@router.post("/tasks", response_model=schemas.AutoAssignmentResponse)
def auto_assign_tasks(
    request: schemas.AssignTasksRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    """
    Автоматически назначает неназначенные задачи в проекте на участников проекта
    используя алгоритм оптимального распределения.
    
    Параметр optimize_for определяет стратегию оптимизации:
    - "balanced" - сбалансированное распределение (по умолчанию)
    - "workload" - приоритет равномерной загрузки
    - "skills" - приоритет соответствия навыков
    - "priority" - приоритет важности задач
    """
    # Проверяем, существует ли проект
    db_project = crud.get_project(db, project_id=request.project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Проверяем, является ли пользователь участником проекта
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Проверяем, что в проекте есть участники
    if not db_project.members:
        raise HTTPException(status_code=400, detail="Project has no members to assign tasks to")
    
    # Валидируем значение optimize_for
    valid_strategies = ["balanced", "workload", "skills", "priority"]
    if request.optimize_for not in valid_strategies:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid optimization strategy. Must be one of: {', '.join(valid_strategies)}"
        )
    
    # Вызываем функцию назначения задач
    try:
        result = assign.assign_tasks(db, request.project_id, request.optimize_for)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 