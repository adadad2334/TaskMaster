import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.routers import projects
from .conftest import test_db_session, auth_headers, test_user, client  # добавлен импорт client
from app.main import app
from app.database import Base, get_db
from app.models import User, Project

def test_create_project(test_db_session: Session, auth_headers: dict):
    """Проверяет создание проекта"""
    # Создаем проект через CRUD
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    assert project is not None
    assert project.name == "Test Project"
    assert project.description == "Test Description"

def test_read_projects(test_db_session: Session, auth_headers: dict):
    """Проверяет получение списка проектов"""
    # Создаем проекты
    for i in range(3):
        crud.create_project(
            db=test_db_session,
            project=schemas.ProjectCreate(
                name=f"Test Project {i}",
                description=f"Test Description {i}"
            )
        )
    test_db_session.commit()
    
    # Получаем список проектов
    response = client.get("/projects/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что получены все проекты
    assert len(data) >= 3  # Может быть больше из-за других тестов
    
    # Проверяем имя первого проекта
    assert any(project["name"] == "Test Project 0" for project in data)

def test_read_project(test_db_session: Session, auth_headers: dict):
    """Проверяет получение проекта по id"""
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    test_db_session.commit()
    
    # Получаем проект по id
    response = client.get(f"/projects/{project.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем данные проекта
    assert data["id"] == project.id
    assert data["name"] == "Test Project"
    assert data["description"] == "Test Description"

def test_update_project(test_db_session: Session, auth_headers: dict):
    """Проверяет обновление проекта"""
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    test_db_session.commit()
    
    # Обновляем проект через CRUD
    updated_project = crud.update_project(
        db=test_db_session,
        project_id=project.id,
        project=schemas.ProjectUpdate(
            name="Updated Project",
            description="Updated Description"
        )
    )
    
    assert updated_project is not None
    assert updated_project.name == "Updated Project"
    assert updated_project.description == "Updated Description"

def test_delete_project(test_db_session: Session, auth_headers: dict):
    """Проверяет удаление проекта"""
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    test_db_session.commit()
    
    # Удаляем проект через CRUD
    result = crud.delete_project(
        db=test_db_session,
        project_id=project.id
    )
    
    assert result is True
    
    # Проверяем, что проект удален из БД
    deleted_project = test_db_session.query(models.Project).filter(models.Project.id == project.id).first()
    assert deleted_project is None

def test_read_project_not_found(test_db_session: Session, auth_headers: dict):
    with pytest.raises(HTTPException) as exc_info:
        projects.read_project(
            project_id=999,
            db=test_db_session,
            current_user=crud.get_user_by_username(test_db_session, "testuser")
        )
    
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Project not found"

def test_update_project_not_member(test_db_session: Session, auth_headers: dict):
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Пытаемся обновить проект без прав
    update_data = schemas.ProjectUpdate(
        name="Updated Name",
        description="Updated Description"
    )
    
    with pytest.raises(HTTPException) as exc_info:
        projects.update_project(
            project_id=project.id,
            project=update_data,
            db=test_db_session,
            current_user=crud.get_user_by_username(test_db_session, "testuser")
        )
    
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not enough permissions"

def test_add_member_to_project(test_db_session: Session, auth_headers: dict):
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Создаем нового пользователя
    new_user = crud.create_user(
        db=test_db_session,
        user=schemas.UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123"
        )
    )
    
    # Добавляем первого пользователя в проект
    user = crud.get_user_by_username(test_db_session, "testuser")
    crud.add_user_to_project(test_db_session, project.id, user.id)
    
    # Добавляем нового пользователя в проект
    response = projects.add_member_to_project(
        project_id=project.id,
        user_id=new_user.id,
        db=test_db_session,
        current_user=user
    )
    
    assert len(response.members) == 2
    assert new_user in response.members

def test_remove_member_from_project(test_db_session: Session, auth_headers: dict):
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Создаем нового пользователя
    new_user = crud.create_user(
        db=test_db_session,
        user=schemas.UserCreate(
            username="newuser",
            email="new@example.com",
            password="password123"
        )
    )
    
    # Добавляем обоих пользователей в проект
    user = crud.get_user_by_username(test_db_session, "testuser")
    crud.add_user_to_project(test_db_session, project.id, user.id)
    crud.add_user_to_project(test_db_session, project.id, new_user.id)
    
    # Удаляем нового пользователя из проекта
    response = projects.remove_member_from_project(
        project_id=project.id,
        user_id=new_user.id,
        db=test_db_session,
        current_user=user
    )
    
    assert len(response.members) == 1
    assert new_user not in response.members

def test_remove_last_member_from_project(test_db_session: Session, auth_headers: dict):
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Добавляем пользователя в проект
    user = crud.get_user_by_username(test_db_session, "testuser")
    crud.add_user_to_project(test_db_session, project.id, user.id)
    
    # Пытаемся удалить последнего пользователя
    with pytest.raises(HTTPException) as exc_info:
        projects.remove_member_from_project(
            project_id=project.id,
            user_id=user.id,
            db=test_db_session,
            current_user=user
        )
    
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Cannot remove the last member from project"

def test_add_user_to_project(test_db_session: Session, test_user: User):
    """Тестирует добавление пользователя в проект"""
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Project with Users",
            description="Testing user management"
        )
    )
    
    # Создаем пользователя
    user = test_user
    
    # Добавляем пользователя в проект
    result = crud.add_user_to_project(
        db=test_db_session,
        project_id=project.id,
        user_id=user.id
    )
    
    assert result is not None
    assert user in project.members
    
    # Обновляем проект из БД и проверяем, что пользователь добавлен
    test_db_session.refresh(project)
    assert user in project.members

def test_remove_user_from_project(test_db_session: Session, test_user: User):
    """Тестирует удаление пользователя из проекта"""
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Project for User Removal",
            description="Testing user removal"
        )
    )
    
    # Получаем пользователя
    user = test_user
    
    # Добавляем пользователя в проект
    crud.add_user_to_project(
        db=test_db_session,
        project_id=project.id,
        user_id=user.id
    )
    
    # Проверяем, что пользователь был добавлен
    test_db_session.refresh(project)
    assert user in project.members
    
    # Удаляем пользователя из проекта
    result = crud.remove_user_from_project(
        db=test_db_session,
        project_id=project.id,
        user_id=user.id
    )
    
    assert result is not None
    
    # Обновляем проект из БД и проверяем, что пользователь удален
    test_db_session.refresh(project)
    assert user not in project.members 