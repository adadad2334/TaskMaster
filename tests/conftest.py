import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
import uuid

# Important - import the app correctly from app.main
from app.main import app as fastapi_app
from app.database import Base, get_db
from app.models import User, Project, Task, Skill, project_user, user_skill, task_skill
from app import crud, models, schemas
from app.auth import get_password_hash

# Переопределяем секретный ключ для тестов
import app.auth
app.auth.SECRET_KEY = "test_secret_key"

# Создаем тестовую базу данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем временный клиент для тестирования API
client = TestClient(fastapi_app)

# Создаем контекст хэширования для тестов
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Фикстура для создания тестовой базы данных
@pytest.fixture(scope="function")
def test_db_session():
    # Создаем таблицы базы данных заново перед каждым тестом
    Base.metadata.create_all(bind=engine)
    
    # Создаем сессию базы данных
    session = TestingSessionLocal()
    
    # Переопределяем зависимость БД в FastAPI для тестов
    def override_get_db():
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
    
    # Подменяем зависимость в приложении
    fastapi_app.dependency_overrides[get_db] = override_get_db
    
    # Отдаем сессию тесту
    yield session
    
    # Очищаем после теста
    session.close()
    Base.metadata.drop_all(bind=engine)

# Фикстура для создания тестового пользователя
@pytest.fixture(scope="function")
def test_user(test_db_session: Session):
    # Создаем тестового пользователя
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("password"),
        is_active=True,
        workload_capacity=100.0,
        current_workload=0.0
    )
    test_db_session.add(user)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user

# Фикстура для заголовков авторизации
@pytest.fixture(scope="function")
def auth_headers(test_user: User):
    # Получаем токен через login endpoint
    login_response = client.post(
        "/users/token",
        data={"username": "testuser", "password": "password"}
    )
    token = login_response.json()["access_token"]
    
    # Возвращаем заголовок с токеном
    return {"Authorization": f"Bearer {token}"}

# Фикстура для создания тестового проекта с пользователями и задачами
@pytest.fixture(scope="function")
def setup_project_with_users_and_tasks(test_db_session: Session, auth_headers: dict):
    # Регистрируем основного пользователя
    client.post(
        "/users/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password",
            "workload_capacity": 100.0,
            "current_workload": 0.0
        }
    )
    
    # Получаем токен для дальнейших запросов
    token_response = client.post(
        "/users/token",
        data={"username": "testuser", "password": "password"}
    )
    
    # Создаем проект
    project_response = client.post(
        "/projects/",
        json={"name": "Test Project", "description": "Test Project Description"},
        headers=auth_headers
    )
    project_id = project_response.json()["id"]
    
    # Создаем 3 дополнительных пользователя
    user_ids = []
    for i in range(3):
        user_response = client.post(
            "/users/register",
            json={
                "username": f"user{i+1}",
                "email": f"user{i+1}@example.com",
                "password": "password",
                "workload_capacity": 100.0,
                "current_workload": 0.0
            }
        )
        user_ids.append(user_response.json()["id"])
    
    # Добавляем пользователей в проект
    for user_id in user_ids:
        client.post(
            f"/projects/{project_id}/members/{user_id}",
            headers=auth_headers
        )
    
    # Создаем навыки
    skill_ids = []
    for i in range(4):
        skill_response = client.post(
            "/skills/",
            json={"name": f"Skill {i+1}", "description": f"Skill {i+1} Description"},
            headers=auth_headers
        )
        skill_ids.append(skill_response.json()["id"])
    
    # Добавляем навыки пользователям
    client.post(f"/users/{user_ids[0]}/skills/{skill_ids[0]}?level=5", headers=auth_headers)
    client.post(f"/users/{user_ids[0]}/skills/{skill_ids[1]}?level=3", headers=auth_headers)
    client.post(f"/users/{user_ids[1]}/skills/{skill_ids[1]}?level=4", headers=auth_headers)
    client.post(f"/users/{user_ids[1]}/skills/{skill_ids[2]}?level=4", headers=auth_headers)
    client.post(f"/users/{user_ids[2]}/skills/{skill_ids[0]}?level=2", headers=auth_headers)
    client.post(f"/users/{user_ids[2]}/skills/{skill_ids[2]}?level=3", headers=auth_headers)
    client.post(f"/users/{user_ids[2]}/skills/{skill_ids[3]}?level=5", headers=auth_headers)
    
    # Создаем задачи
    task_ids = []
    task_data = [
        {
            "title": "Task 1", 
            "description": "Task 1 Description",
            "project_id": project_id,
            "status": "TODO",
            "priority": "HIGH",
            "estimated_hours": 10.0
        },
        {
            "title": "Task 2", 
            "description": "Task 2 Description",
            "project_id": project_id,
            "status": "TODO",
            "priority": "MEDIUM",
            "estimated_hours": 5.0
        },
        {
            "title": "Task 3", 
            "description": "Task 3 Description",
            "project_id": project_id,
            "status": "TODO",
            "priority": "LOW",
            "estimated_hours": 3.0
        },
        {
            "title": "Task 4", 
            "description": "Task 4 Description",
            "project_id": project_id,
            "status": "TODO",
            "priority": "MEDIUM",
            "estimated_hours": 8.0
        }
    ]
    
    for task in task_data:
        task_response = client.post("/tasks/", json=task, headers=auth_headers)
        task_ids.append(task_response.json()["id"])
    
    return {
        "project_id": project_id,
        "user_ids": user_ids,
        "skill_ids": skill_ids,
        "task_ids": task_ids
    } 