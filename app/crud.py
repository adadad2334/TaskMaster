from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import and_

from . import models, schemas, auth

"""
CRUD operations module.
This module provides Create, Read, Update, Delete operations for all models.
"""

# CRUD для пользователей
def get_user(db: Session, user_id: int):
    """Get user by ID."""
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """
    Get a user by email (case-insensitive).
    
    Args:
        db: Database session
        email: Email to search for
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    return db.query(models.User).filter(models.User.email.ilike(email)).first()

def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """
    Get a user by username (case-insensitive).
    
    Args:
        db: Database session
        username: Username to search for
        
    Returns:
        Optional[User]: User if found, None otherwise
    """
    return db.query(models.User).filter(models.User.username.ilike(username)).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get list of users with pagination."""
    return db.query(models.User).offset(skip).limit(limit).all()

def create_user(db: Session, user: schemas.UserCreate):
    """Create a new user."""
    # Check for existing username
    existing_user = get_user_by_username(db, user.username)
    if existing_user:
        return None
    
    # Check for existing email
    existing_email = get_user_by_email(db, user.email)
    if existing_email:
        return None
    
    # Create new user
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password,
        workload_capacity=user.workload_capacity,
        current_workload=0.0
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user: schemas.UserUpdate):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        return None

    update_data = user.model_dump(exclude_unset=True)
    
    if "password" in update_data:
        update_data["hashed_password"] = auth.get_password_hash(update_data.pop("password"))
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False

# CRUD для навыков
def get_skill(db: Session, skill_id: int):
    return db.query(models.Skill).filter(models.Skill.id == skill_id).first()

def get_skill_by_name(db: Session, name: str):
    return db.query(models.Skill).filter(models.Skill.name == name).first()

def get_skills(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Skill).offset(skip).limit(limit).all()

def create_skill(db: Session, skill: schemas.SkillCreate):
    db_skill = models.Skill(**skill.model_dump())
    db.add(db_skill)
    db.commit()
    db.refresh(db_skill)
    return db_skill

def delete_skill(db: Session, skill_id: int):
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    if db_skill:
        db.delete(db_skill)
        db.commit()
        return True
    return False

# Управление навыками пользователя
def add_skill_to_user(db: Session, user_id: int, skill_id: int, level: int = 1):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    
    if not db_user or not db_skill:
        return None
    
    # Проверка, есть ли уже такой навык у пользователя
    stmt = db.query(models.user_skill).filter(
        and_(
            models.user_skill.c.user_id == user_id,
            models.user_skill.c.skill_id == skill_id
        )
    ).first()
    
    if stmt:
        # Обновляем уровень навыка
        db.execute(
            models.user_skill.update()
            .where(
                and_(
                    models.user_skill.c.user_id == user_id,
                    models.user_skill.c.skill_id == skill_id
                )
            )
            .values(level=level)
        )
    else:
        # Добавляем новый навык
        db.execute(
            models.user_skill.insert().values(
                user_id=user_id,
                skill_id=skill_id,
                level=level
            )
        )
    
    db.commit()
    return db_user

def remove_skill_from_user(db: Session, user_id: int, skill_id: int):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    
    if not db_user or not db_skill:
        return None
    
    db.execute(
        models.user_skill.delete()
        .where(
            and_(
                models.user_skill.c.user_id == user_id,
                models.user_skill.c.skill_id == skill_id
            )
        )
    )
    
    db.commit()
    return db_user

# Управление навыками задач
def add_skill_to_task(db: Session, task_id: int, skill_id: int, required_level: int = 1):
    """
    Добавляет навык к задаче или обновляет требуемый уровень
    """
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    
    if not db_task or not db_skill:
        return None
    
    # Проверка, есть ли уже такой навык у задачи
    stmt = db.query(models.task_skill).filter(
        and_(
            models.task_skill.c.task_id == task_id,
            models.task_skill.c.skill_id == skill_id
        )
    ).first()
    
    if stmt:
        # Обновляем требуемый уровень навыка
        db.execute(
            models.task_skill.update()
            .where(
                and_(
                    models.task_skill.c.task_id == task_id,
                    models.task_skill.c.skill_id == skill_id
                )
            )
            .values(required_level=required_level)
        )
    else:
        # Добавляем новый навык
        db.execute(
            models.task_skill.insert().values(
                task_id=task_id,
                skill_id=skill_id,
                required_level=required_level
            )
        )
    
    db.commit()
    return db_task

def remove_skill_from_task(db: Session, task_id: int, skill_id: int):
    """
    Удаляет навык из задачи
    """
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
    
    if not db_task or not db_skill:
        return None
    
    db.execute(
        models.task_skill.delete()
        .where(
            and_(
                models.task_skill.c.task_id == task_id,
                models.task_skill.c.skill_id == skill_id
            )
        )
    )
    
    db.commit()
    return db_task

# CRUD для проектов
def get_project(db: Session, project_id: int):
    return db.query(models.Project).filter(models.Project.id == project_id).first()

def get_project_by_name(db: Session, name: str):
    return db.query(models.Project).filter(models.Project.name == name).first()

def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Project).offset(skip).limit(limit).all()

def create_project(db: Session, project: schemas.ProjectCreate):
    db_project = models.Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project

def update_project(db: Session, project_id: int, project: schemas.ProjectUpdate):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not db_project:
        return None

    update_data = project.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_project, key, value)
    
    db.commit()
    db.refresh(db_project)
    return db_project

def delete_project(db: Session, project_id: int):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if db_project:
        db.delete(db_project)
        db.commit()
        return True
    return False

# Управление участниками проекта
def add_user_to_project(db: Session, project_id: int, user_id: int):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not db_project or not db_user:
        return None
    
    # Проверка, есть ли уже пользователь в проекте
    stmt = db.query(models.project_user).filter(
        and_(
            models.project_user.c.project_id == project_id,
            models.project_user.c.user_id == user_id
        )
    ).first()
    
    if not stmt:
        db.execute(
            models.project_user.insert().values(
                project_id=project_id,
                user_id=user_id
            )
        )
        
        db.commit()
    
    return db_project

def remove_user_from_project(db: Session, project_id: int, user_id: int):
    db_project = db.query(models.Project).filter(models.Project.id == project_id).first()
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not db_project or not db_user:
        return None
    
    db.execute(
        models.project_user.delete()
        .where(
            and_(
                models.project_user.c.project_id == project_id,
                models.project_user.c.user_id == user_id
            )
        )
    )
    
    db.commit()
    return db_project

# CRUD для задач
def get_task(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()

def get_tasks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Task).offset(skip).limit(limit).all()

def get_project_tasks(db: Session, project_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Task).filter(models.Task.project_id == project_id).offset(skip).limit(limit).all()

def get_user_tasks(db: Session, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Task).filter(models.Task.assignee_id == user_id).offset(skip).limit(limit).all()

def create_task(db: Session, task: schemas.TaskCreate):
    task_data = task.model_dump(exclude={"required_skills"})
    db_task = models.Task(**task_data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    # Добавляем требуемые навыки к задаче
    if task.required_skills:
        for skill_id in task.required_skills:
            db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
            if db_skill:
                db.execute(
                    models.task_skill.insert().values(
                        task_id=db_task.id,
                        skill_id=skill_id,
                        required_level=1  # По умолчанию уровень 1
                    )
                )
        db.commit()
    
    return db_task

def update_task(db: Session, task_id: int, task: schemas.TaskUpdate):
    """Update task by ID."""
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        return None

    # Обновляем поля задачи
    update_data = task.model_dump(exclude={"required_skills"}, exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_task, key, value)
    
    # Если изменился исполнитель, обновляем workload
    if "assignee_id" in update_data:
        if db_task.assignee_id:  # Если был предыдущий исполнитель
            prev_assignee = db.query(models.User).filter(models.User.id == db_task.assignee_id).first()
            if prev_assignee:
                prev_assignee.current_workload = max(prev_assignee.current_workload - db_task.estimated_hours, 0)
        
        if update_data["assignee_id"]:  # Если назначен новый исполнитель
            new_assignee = db.query(models.User).filter(models.User.id == update_data["assignee_id"]).first()
            if new_assignee:
                new_assignee.current_workload += db_task.estimated_hours
    
    # Обновляем навыки, если они предоставлены
    if task.required_skills is not None:
        # Удаляем все текущие навыки
        db.execute(
            models.task_skill.delete()
            .where(models.task_skill.c.task_id == task_id)
        )
        
        # Добавляем новые навыки
        for skill_id in task.required_skills:
            db_skill = db.query(models.Skill).filter(models.Skill.id == skill_id).first()
            if db_skill:
                db.execute(
                    models.task_skill.insert().values(
                        task_id=task_id,
                        skill_id=skill_id,
                        required_level=1
                    )
                )
    
    db.commit()
    db.refresh(db_task)
    return db_task

def update_task_status(db: Session, task_id: int, status: models.TaskStatus):
    """
    Обновляет статус задачи и устанавливает completed_at для завершенных задач
    """
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not db_task:
        return None
    
    # Устанавливаем новый статус
    db_task.status = status
    
    # Если статус DONE, устанавливаем дату завершения
    if status == models.TaskStatus.DONE and not db_task.completed_at:
        db_task.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_task(db: Session, task_id: int):
    """Delete task by ID."""
    db_task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if db_task:
        # Уменьшаем workload пользователя, если задача была назначена
        if db_task.assignee_id:
            assignee = db.query(models.User).filter(models.User.id == db_task.assignee_id).first()
            if assignee:
                assignee.current_workload = max(assignee.current_workload - db_task.estimated_hours, 0)
        
        db.delete(db_task)
        db.commit()
        return True
    return False

def update_assignee_workload(db: Session, assignee: models.User, task: models.Task) -> None:
    """Update assignee workload after task assignment."""
    assignee.current_workload = max(assignee.current_workload - task.estimated_hours, 0)
    db.commit()

def get_user_skills(db: Session, user_id: int):
    """Get all skills for a user with skill levels.
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        List of user_skill association items
    """
    return db.query(models.user_skill).filter(models.user_skill.c.user_id == user_id).all()

def get_task_skills(db: Session, task_id: int):
    """Get all skills required for a task with required levels.
    
    Args:
        db: Database session
        task_id: ID of the task
        
    Returns:
        List of task_skill association items
    """
    return db.query(models.task_skill).filter(models.task_skill.c.task_id == task_id).all() 