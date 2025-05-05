import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, Project, Task, Skill, user_skill, task_skill

# Используем ту же тестовую БД и клиент, что и в других тестах
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
def setup_project_with_users_and_tasks(auth_headers):
    # 1. Создаем проект
    project_response = client.post(
        "/projects/",
        json={
            "name": "Assignment Test Project",
            "description": "Project for testing task assignment"
        },
        headers=auth_headers
    )
    project_id = project_response.json()["id"]
    
    # 2. Создаем дополнительных пользователей
    user_ids = []
    for i in range(3):
        user_response = client.post(
            "/users/register",
            json={
                "username": f"user{i}",
                "email": f"user{i}@example.com",
                "password": "password123",
                "workload_capacity": 100.0
            }
        )
        user_ids.append(user_response.json()["id"])
    
    # 3. Добавляем пользователей в проект
    for user_id in user_ids:
        client.post(
            f"/projects/{project_id}/members/{user_id}",
            headers=auth_headers
        )
    
    # 4. Создаем навыки
    skill_ids = []
    for skill_name in ["Python", "JavaScript", "SQL", "UI/UX"]:
        skill_response = client.post(
            "/skills/",
            json={
                "name": skill_name,
                "description": f"Skill in {skill_name}"
            },
            headers=auth_headers
        )
        skill_ids.append(skill_response.json()["id"])
    
    # 5. Добавляем навыки пользователям
    # Первый пользователь: Python (уровень 5), JavaScript (уровень 3)
    client.post(
        f"/users/{user_ids[0]}/skills/{skill_ids[0]}",
        params={"level": 5},
        headers=auth_headers
    )
    client.post(
        f"/users/{user_ids[0]}/skills/{skill_ids[1]}",
        params={"level": 3},
        headers=auth_headers
    )
    
    # Второй пользователь: JavaScript (уровень 4), SQL (уровень 4)
    client.post(
        f"/users/{user_ids[1]}/skills/{skill_ids[1]}",
        params={"level": 4},
        headers=auth_headers
    )
    client.post(
        f"/users/{user_ids[1]}/skills/{skill_ids[2]}",
        params={"level": 4},
        headers=auth_headers
    )
    
    # Третий пользователь: Python (уровень 2), SQL (уровень 3), UI/UX (уровень 5)
    client.post(
        f"/users/{user_ids[2]}/skills/{skill_ids[0]}",
        params={"level": 2},
        headers=auth_headers
    )
    client.post(
        f"/users/{user_ids[2]}/skills/{skill_ids[2]}",
        params={"level": 3},
        headers=auth_headers
    )
    client.post(
        f"/users/{user_ids[2]}/skills/{skill_ids[3]}",
        params={"level": 5},
        headers=auth_headers
    )
    
    # 6. Создаем задачи без назначения
    task_ids = []
    
    # Задача 1: Python
    task1_response = client.post(
        "/tasks/",
        json={
            "title": "Python Task",
            "description": "Task requiring Python",
            "status": "todo",
            "priority": "high",
            "estimated_hours": 5.0,
            "project_id": project_id,
            "required_skills": [skill_ids[0]]  # Python
        },
        headers=auth_headers
    )
    task_ids.append(task1_response.json()["id"])
    
    # Задача 2: JavaScript
    task2_response = client.post(
        "/tasks/",
        json={
            "title": "JavaScript Task",
            "description": "Task requiring JavaScript",
            "status": "todo",
            "priority": "medium",
            "estimated_hours": 3.0,
            "project_id": project_id,
            "required_skills": [skill_ids[1]]  # JavaScript
        },
        headers=auth_headers
    )
    task_ids.append(task2_response.json()["id"])
    
    # Задача 3: SQL
    task3_response = client.post(
        "/tasks/",
        json={
            "title": "SQL Task",
            "description": "Task requiring SQL",
            "status": "todo",
            "priority": "low",
            "estimated_hours": 2.0,
            "project_id": project_id,
            "required_skills": [skill_ids[2]]  # SQL
        },
        headers=auth_headers
    )
    task_ids.append(task3_response.json()["id"])
    
    # Задача 4: UI/UX
    task4_response = client.post(
        "/tasks/",
        json={
            "title": "UI/UX Task",
            "description": "Task requiring UI/UX",
            "status": "todo",
            "priority": "critical",
            "estimated_hours": 8.0,
            "project_id": project_id,
            "required_skills": [skill_ids[3]]  # UI/UX
        },
        headers=auth_headers
    )
    task_ids.append(task4_response.json()["id"])
    
    return {
        "project_id": project_id,
        "user_ids": user_ids,
        "skill_ids": skill_ids,
        "task_ids": task_ids
    }

def test_task_assignment_balanced(test_db, auth_headers, setup_project_with_users_and_tasks):
    project_id = setup_project_with_users_and_tasks["project_id"]
    
    # Вызываем эндпоинт назначения задач
    response = client.post(
        "/assign/tasks",
        json={
            "project_id": project_id,
            "optimize_for": "balanced"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что есть назначения
    assert "assignments" in data
    # Всего у нас 4 задачи, и все должны быть назначены
    assert len(data["assignments"]) == 4
    
    # Проверяем, что нет неназначенных задач
    assert "unassigned_tasks" in data
    assert len(data["unassigned_tasks"]) == 0

def test_task_assignment_skills(test_db, auth_headers, setup_project_with_users_and_tasks):
    project_id = setup_project_with_users_and_tasks["project_id"]
    
    # Вызываем эндпоинт назначения задач с приоритетом на навыки
    response = client.post(
        "/assign/tasks",
        json={
            "project_id": project_id,
            "optimize_for": "skills"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что задачи назначены
    assert len(data["assignments"]) == 4
    
    # Проверяем, что задачи назначены в соответствии с навыками
    skill_matched_assignments = 0
    for assignment in data["assignments"]:
        # Получаем детали задачи
        task_response = client.get(
            f"/tasks/{assignment['task_id']}",
            headers=auth_headers
        )
        task = task_response.json()
        
        # Получаем детали пользователя
        user_response = client.get(
            f"/users/{assignment['assignee_id']}",
            headers=auth_headers
        )
        user = user_response.json()
        
        # Проверяем соответствие навыков
        user_skill_ids = [skill["id"] for skill in user["skills"]]
        task_skill_ids = [skill["id"] for skill in task["required_skills"]]
        
        if any(skill_id in user_skill_ids for skill_id in task_skill_ids):
            skill_matched_assignments += 1
    
    # В нашем тесте все задачи должны быть назначены пользователям с соответствующими навыками
    assert skill_matched_assignments == 4

def test_task_assignment_workload(test_db, auth_headers, setup_project_with_users_and_tasks):
    project_id = setup_project_with_users_and_tasks["project_id"]
    
    # Вызываем эндпоинт назначения задач с приоритетом на рабочую нагрузку
    response = client.post(
        "/assign/tasks",
        json={
            "project_id": project_id,
            "optimize_for": "workload"
        },
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что задачи назначены
    assert len(data["assignments"]) == 4
    
    # Проверяем, что назначения распределены между пользователями
    assignee_counts = {}
    for assignment in data["assignments"]:
        assignee_id = assignment["assignee_id"]
        if assignee_id in assignee_counts:
            assignee_counts[assignee_id] += 1
        else:
            assignee_counts[assignee_id] = 1
    
    # В идеале каждый пользователь должен получить хотя бы одну задачу
    # для равномерного распределения рабочей нагрузки
    assert len(assignee_counts) >= 3 