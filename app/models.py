from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Enum, Float, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from .database import Base

# Ассоциативная таблица для связи многие-ко-многим между пользователями и проектами
project_user = Table(
    "project_user",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("project_id", Integer, ForeignKey("projects.id"))
)

# Ассоциативная таблица для связи многие-ко-многим между пользователями и навыками
user_skill = Table(
    "user_skill",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id")),
    Column("skill_id", Integer, ForeignKey("skills.id")),
    Column("level", Integer, default=1)  # Уровень навыка от 1 до 5
)

# Ассоциативная таблица для связи многие-ко-многим между задачами и требуемыми навыками
task_skill = Table(
    "task_skill",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id")),
    Column("skill_id", Integer, ForeignKey("skills.id")),
    Column("required_level", Integer, default=1)  # Необходимый уровень навыка
)

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    REVIEW = "review"
    DONE = "done"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    workload_capacity = Column(Float, default=100.0)  # Максимальная загрузка пользователя (в часах в неделю)
    current_workload = Column(Float, default=0.0)  # Текущая загрузка пользователя

    # Отношения
    tasks = relationship("Task", back_populates="assignee")
    projects = relationship("Project", secondary=project_user, back_populates="members")
    skills = relationship("Skill", secondary=user_skill, back_populates="users")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Отношения
    tasks = relationship("Task", back_populates="project")
    members = relationship("User", secondary=project_user, back_populates="projects")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(String)
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    estimated_hours = Column(Float, default=1.0)  # Оценка трудозатрат в часах

    # Внешние ключи
    project_id = Column(Integer, ForeignKey("projects.id"))
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Отношения
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")
    required_skills = relationship("Skill", secondary=task_skill, back_populates="tasks")

class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    
    # Отношения
    users = relationship("User", secondary=user_skill, back_populates="skills")
    tasks = relationship("Task", secondary=task_skill, back_populates="required_skills") 