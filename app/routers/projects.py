"""
Projects router module.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, crud
from ..database import get_db
from ..auth import get_current_active_user

router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Project)
def create_project(project: schemas.ProjectCreate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_active_user)):
    db_project = crud.create_project(db=db, project=project)
    
    # Автоматически добавляем создателя проекта как участника
    crud.add_user_to_project(db, project_id=db_project.id, user_id=current_user.id)
    
    # Обновляем проект для получения обновленных данных
    return crud.get_project(db, project_id=db_project.id)

@router.get("/", response_model=List[schemas.Project])
def read_projects(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                 current_user: models.User = Depends(get_current_active_user)):
    projects = crud.get_projects(db, skip=skip, limit=limit)
    return projects

@router.get("/{project_id}", response_model=schemas.Project)
def read_project(project_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_active_user)):
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return db_project

@router.put("/{project_id}", response_model=schemas.Project)
def update_project(project_id: int, project: schemas.ProjectUpdate, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_active_user)):
    # Проверяем, что пользователь является участником проекта
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_project = crud.update_project(db, project_id=project_id, project=project)
    return db_project

@router.delete("/{project_id}", response_model=bool)
def delete_project(project_id: int, db: Session = Depends(get_db),
                  current_user: models.User = Depends(get_current_active_user)):
    # Проверяем, что пользователь является участником проекта
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    result = crud.delete_project(db, project_id=project_id)
    return result

@router.post("/{project_id}/members/{user_id}", response_model=schemas.Project)
def add_member_to_project(project_id: int, user_id: int, db: Session = Depends(get_db),
                          current_user: models.User = Depends(get_current_active_user)):
    # Проверяем, что текущий пользователь является участником проекта
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Проверяем, что пользователь существует
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_project = crud.add_user_to_project(db, project_id=project_id, user_id=user_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project or user not found")
    
    return db_project

@router.delete("/{project_id}/members/{user_id}", response_model=schemas.Project)
def remove_member_from_project(project_id: int, user_id: int, db: Session = Depends(get_db),
                               current_user: models.User = Depends(get_current_active_user)):
    # Проверяем, что текущий пользователь является участником проекта
    db_project = crud.get_project(db, project_id=project_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if current_user not in db_project.members:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Нельзя удалить последнего участника проекта
    if len(db_project.members) <= 1 and user_id in [member.id for member in db_project.members]:
        raise HTTPException(status_code=400, detail="Cannot remove the last member from project")
    
    db_project = crud.remove_user_from_project(db, project_id=project_id, user_id=user_id)
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project or user not found")
    
    return db_project 