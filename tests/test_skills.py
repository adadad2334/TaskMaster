import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app import crud, models, schemas
from .conftest import test_db_session, auth_headers, test_user, client

def test_create_skill(test_db_session: Session, auth_headers: dict):
    """Проверяет создание навыка"""
    response = client.post(
        "/skills/",
        json={"name": "Test Skill", "description": "Test Description"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что навык создан в БД
    skill = crud.get_skill(test_db_session, data["id"])
    assert skill is not None
    assert skill.name == "Test Skill"
    assert skill.description == "Test Description"

def test_read_skills(test_db_session: Session, auth_headers: dict):
    """Проверяет получение списка навыков"""
    # Создаем навыки
    for i in range(3):
        crud.create_skill(
            db=test_db_session,
            skill=schemas.SkillCreate(
                name=f"Test Skill {i}",
                description=f"Test Description {i}"
            )
        )
    
    test_db_session.commit()
    
    # Получаем список навыков через API
    response = client.get("/skills/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что получены навыки
    assert len(data) >= 3  # Может быть больше из-за других тестов
    
    # Проверяем имя первого навыка
    assert any(skill["name"] == "Test Skill 0" for skill in data)

def test_read_skill(test_db_session: Session, auth_headers: dict):
    """Проверяет получение навыка по id"""
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Test Skill",
            description="Test Description"
        )
    )
    
    test_db_session.commit()
    
    # Получаем навык по id через API
    response = client.get(f"/skills/{skill.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем данные навыка
    assert data["id"] == skill.id
    assert data["name"] == "Test Skill"
    assert data["description"] == "Test Description"

def test_update_skill(test_db_session: Session, auth_headers: dict):
    """Проверяет обновление навыка"""
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Original Skill",
            description="Original Description"
        )
    )
    
    test_db_session.commit()
    
    # Обновляем навык через API
    response = client.put(
        f"/skills/{skill.id}",
        json={"name": "Updated Skill", "description": "Updated Description"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что навык обновлен
    assert data["name"] == "Updated Skill"
    assert data["description"] == "Updated Description"
    
    # Проверяем, что навык обновлен в БД
    updated_skill = crud.get_skill(test_db_session, skill.id)
    assert updated_skill.name == "Updated Skill"
    assert updated_skill.description == "Updated Description"

def test_delete_skill(test_db_session: Session, auth_headers: dict):
    """Проверяет удаление навыка"""
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Test Skill",
            description="Test Description"
        )
    )
    
    test_db_session.commit()
    
    # Удаляем навык через API
    response = client.delete(f"/skills/{skill.id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем, что навык удален из БД
    deleted_skill = crud.get_skill(test_db_session, skill.id)
    assert deleted_skill is None

def test_add_skill_to_user(test_db_session: Session, auth_headers: dict, test_user: User):
    """Проверяет добавление навыка пользователю"""
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Test Skill",
            description="Test Description"
        )
    )
    
    test_db_session.commit()
    
    user = test_user
    
    # Добавляем навык пользователю через API
    response = client.post(
        f"/users/{user.id}/skills/{skill.id}?level=4",
        headers=auth_headers
    )
    
    # Check status code
    assert response.status_code == 200
    
    # Проверяем, что навык добавлен пользователю в БД
    user_skills = crud.get_user_skills(test_db_session, user.id)
    assert any(us.skill_id == skill.id and us.level == 4 for us in user_skills)

def test_add_skill_to_task(test_db_session: Session, auth_headers: dict, test_user: User):
    """Проверяет добавление навыка к задаче"""
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Добавляем пользователя в проект
    user = test_user
    crud.add_user_to_project(test_db_session, project.id, user.id)
    
    # Создаем задачу
    task = crud.create_task(
        db=test_db_session,
        task=schemas.TaskCreate(
            title="Test Task",
            description="Test Description",
            project_id=project.id,
            status=models.TaskStatus.TODO,
            priority=models.TaskPriority.MEDIUM,
            estimated_hours=5.0
        )
    )
    
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Test Skill",
            description="Test Description"
        )
    )
    
    test_db_session.commit()
    
    # Добавляем навык к задаче через API
    # Проверяем с использованием прямого метода из CRUD (тесты API далее)
    result = crud.add_skill_to_task(
        db=test_db_session,
        task_id=task.id,
        skill_id=skill.id,
        required_level=3
    )
    
    assert result is not None
    
    # Проверяем, что навык добавлен к задаче в БД
    task_skills = crud.get_task_skills(test_db_session, task.id)
    assert any(ts.skill_id == skill.id and ts.required_level == 3 for ts in task_skills)

def test_create_skill_direct(test_db_session: Session):
    """Проверяет создание навыка через CRUD"""
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Direct CRUD Skill",
            description="Created directly through CRUD"
        )
    )
    
    assert skill is not None
    assert skill.name == "Direct CRUD Skill"
    assert skill.description == "Created directly through CRUD"

def test_get_skill(test_db_session: Session):
    """Проверяет получение навыка по ID"""
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Get Test Skill",
            description="For get_skill test"
        )
    )
    
    test_db_session.commit()
    
    # Получаем навык по ID
    retrieved_skill = crud.get_skill(test_db_session, skill.id)
    
    assert retrieved_skill is not None
    assert retrieved_skill.id == skill.id
    assert retrieved_skill.name == "Get Test Skill"
    
    # Проверяем, что несуществующий навык возвращает None
    non_existent_skill = crud.get_skill(test_db_session, 9999)
    assert non_existent_skill is None

def test_delete_skill(test_db_session: Session):
    """Проверяет удаление навыка"""
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Skill To Delete",
            description="This will be deleted"
        )
    )
    
    test_db_session.commit()
    
    # Удаляем навык
    result = crud.delete_skill(test_db_session, skill.id)
    
    assert result is True
    
    # Проверяем, что навык удален
    deleted_skill = crud.get_skill(test_db_session, skill.id)
    assert deleted_skill is None
    
    # Проверяем, что удаление несуществующего навыка возвращает False
    result = crud.delete_skill(test_db_session, 9999)
    assert result is False 