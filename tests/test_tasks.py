import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import json

from app.main import app
from app.database import Base, get_db
from app.models import User, Project, Task, TaskStatus, TaskPriority

# Используем ту же тестовую БД и клиент, что и в test_users.py
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def auth_headers(test_db):
    # Регистрируем пользователя
    client.post(
        "/users/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        },
    )
    
    # Логинимся и получаем токен
    login_response = client.post(
        "/users/token",
        data={
            "username": "testuser",
            "password": "password123"
        },
    )
    token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_project(auth_headers):
    # Создаем тестовый проект
    response = client.post(
        "/projects/",
        json={
            "name": "Test Project",
            "description": "A test project"
        },
        headers=auth_headers
    )
    return response.json()

def test_create_task(test_db, auth_headers, test_project):
    # Создаем задачу
    response = client.post(
        "/tasks/",
        json={
            "title": "Test Task",
            "description": "A test task",
            "status": "todo",
            "priority": "medium",
            "estimated_hours": 5.0,
            "project_id": test_project["id"],
            "required_skills": []
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "A test task"
    assert data["status"] == "todo"
    assert data["priority"] == "medium"
    assert data["estimated_hours"] == 5.0
    assert data["project_id"] == test_project["id"]
    assert "id" in data

def test_get_tasks(test_db, auth_headers, test_project):
    # Создаем задачу
    client.post(
        "/tasks/",
        json={
            "title": "Test Task",
            "description": "A test task",
            "project_id": test_project["id"]
        },
        headers=auth_headers
    )
    
    # Получаем список задач
    response = client.get(
        "/tasks/",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Task"
    assert data[0]["project_id"] == test_project["id"]

def test_get_project_tasks(test_db, auth_headers, test_project):
    # Создаем задачу
    client.post(
        "/tasks/",
        json={
            "title": "Test Task",
            "description": "A test task",
            "project_id": test_project["id"]
        },
        headers=auth_headers
    )
    
    # Получаем список задач проекта
    response = client.get(
        f"/tasks/?project_id={test_project['id']}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Task"
    assert data[0]["project_id"] == test_project["id"]

def test_update_task(test_db, auth_headers, test_project):
    # Создаем задачу
    create_response = client.post(
        "/tasks/",
        json={
            "title": "Test Task",
            "description": "A test task",
            "project_id": test_project["id"]
        },
        headers=auth_headers
    )
    task_id = create_response.json()["id"]
    
    # Обновляем задачу
    response = client.put(
        f"/tasks/{task_id}",
        json={
            "title": "Updated Task",
            "status": "in_progress",
            "priority": "high"
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["description"] == "A test task"  # Не изменилось
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"
    assert data["project_id"] == test_project["id"]

def test_delete_task(test_db, auth_headers, test_project):
    # Создаем задачу
    create_response = client.post(
        "/tasks/",
        json={
            "title": "Test Task",
            "description": "A test task",
            "project_id": test_project["id"]
        },
        headers=auth_headers
    )
    task_id = create_response.json()["id"]
    
    # Удаляем задачу
    response = client.delete(
        f"/tasks/{task_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() is True
    
    # Проверяем, что задача действительно удалена
    response = client.get(
        f"/tasks/{task_id}",
        headers=auth_headers
    )
    assert response.status_code == 404

def test_unauthorized_task_access(test_db, test_project):
    # Пытаемся получить список задач без токена
    response = client.get("/tasks/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated" 