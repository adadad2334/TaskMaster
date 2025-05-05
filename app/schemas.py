from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime
from .models import TaskStatus, TaskPriority

# Схемы для авторизации
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Схемы для навыка
class SkillBase(BaseModel):
    name: str
    description: Optional[str] = None

class SkillCreate(SkillBase):
    pass

class Skill(SkillBase):
    id: int

    class Config:
        orm_mode = True

# Схемы для пользователя
class UserBase(BaseModel):
    username: str
    email: EmailStr
    workload_capacity: Optional[float] = 100.0

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    workload_capacity: Optional[float] = None
    is_active: Optional[bool] = None

class UserSkill(BaseModel):
    skill_id: int
    level: int = Field(ge=1, le=5)

class UserWithSkills(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    current_workload: float
    skills: List[Skill] = []

    class Config:
        orm_mode = True

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    current_workload: float

    class Config:
        orm_mode = True

# Схемы для проекта
class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Project(ProjectBase):
    id: int
    created_at: datetime
    members: List[User] = []

    class Config:
        orm_mode = True

# Схемы для задачи
class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[TaskStatus] = TaskStatus.TODO
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = 1.0
    project_id: int

class TaskCreate(TaskBase):
    required_skills: Optional[List[int]] = []

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    assignee_id: Optional[int] = None
    required_skills: Optional[List[int]] = None

class TaskSkill(BaseModel):
    skill_id: int
    required_level: int = Field(ge=1, le=5)

class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    assignee_id: Optional[int] = None
    required_skills: List[Skill] = []

    class Config:
        orm_mode = True

# Схемы для автоматического назначения
class AssignTasksRequest(BaseModel):
    project_id: int
    optimize_for: Optional[str] = "balanced"  # balanced, workload, skills, priority

class TaskAssignmentResult(BaseModel):
    task_id: int
    assignee_id: int
    assignee_username: str
    match_score: float

class AutoAssignmentResponse(BaseModel):
    assignments: List[TaskAssignmentResult]
    unassigned_tasks: List[int] = [] 