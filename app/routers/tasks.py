"""
Tasks router module.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from .. import models, schemas, crud
from ..database import get_db
from ..auth import get_current_active_user

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_active_user)):
    # Проверяем, что проект существует и пользователь имеет к нему доступ
    db_project = crud.get_project(db, project_id=task.project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Создаем задачу
    return crud.create_task(db=db, task=task)

@router.get("/", response_model=List[schemas.Task])
def read_tasks(skip: int = 0, limit: int = 100, project_id: int = None, 
              db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_active_user)):
    # Если указан ID проекта, проверяем, что пользователь имеет к нему доступ
    if project_id:
        db_project = crud.get_project(db, project_id=project_id)
        if not db_project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        if current_user not in db_project.members:
            raise HTTPException(status_code=403, detail="Not enough permissions")
        
        tasks = crud.get_project_tasks(db, project_id=project_id, skip=skip, limit=limit)
    else:
        # Получаем все задачи, доступные пользователю
        tasks = []
        user_projects = current_user.projects
        for project in user_projects:
            project_tasks = crud.get_project_tasks(db, project_id=project.id)
            tasks.extend(project_tasks)
        
        # Применяем пагинацию вручную
        tasks = tasks[skip:skip+limit]
    
    return tasks

@router.get("/my", response_model=List[schemas.Task])
def read_my_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_active_user)):
    # Получаем задачи, назначенные на текущего пользователя
    tasks = crud.get_user_tasks(db, user_id=current_user.id, skip=skip, limit=limit)
    return tasks

@router.get("/{task_id}", response_model=schemas.Task)
def read_task(task_id: int, db: Session = Depends(get_db),
             current_user: models.User = Depends(get_current_active_user)):
    db_task = crud.get_task(db, task_id=task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Проверяем, имеет ли пользователь доступ к проекту, в котором находится задача
    db_project = crud.get_project(db, project_id=db_task.project_id)
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return db_task

@router.put("/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_active_user)):
    # Проверяем, что задача существует
    db_task = crud.get_task(db, task_id=task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Проверяем, имеет ли пользователь доступ к проекту, в котором находится задача
    db_project = crud.get_project(db, project_id=db_task.project_id)
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Обновляем задачу
    return crud.update_task(db, task_id=task_id, task=task)

@router.delete("/{task_id}", response_model=bool)
def delete_task(task_id: int, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_active_user)):
    # Проверяем, что задача существует
    db_task = crud.get_task(db, task_id=task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Проверяем, имеет ли пользователь доступ к проекту, в котором находится задача
    db_project = crud.get_project(db, project_id=db_task.project_id)
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Удаляем задачу
    result = crud.delete_task(db, task_id=task_id)
    return result 