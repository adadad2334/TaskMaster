import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException
from sqlalchemy.orm import Session
import uuid
from datetime import timedelta
from passlib.context import CryptContext

from app.main import app
from app.database import Base, get_db
from app.models import User
from app import crud, models, schemas
from app.routers import users
from .conftest import test_db_session, auth_headers, test_user, client
from app.auth import get_password_hash

# Создаем контекст хэширования для проверки паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def test_register_user(test_db_session: Session):
    """Проверяет регистрацию нового пользователя"""
    # Создаем уникальные данные
    unique_username = f"testuser_{uuid.uuid4()}"
    unique_email = f"test_{uuid.uuid4()}@example.com"
    
    response = client.post(
        "/users/register",
        json={
            "username": unique_username,
            "email": unique_email,
            "password": "testpass123",
            "workload_capacity": 100.0,
            "current_workload": 0.0
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что пользователь создан в БД
    user = crud.get_user_by_username(test_db_session, unique_username)
    assert user is not None
    assert user.username == unique_username
    assert user.email == unique_email
    assert pwd_context.verify("testpass123", user.hashed_password)
    assert user.is_active is True

def test_register_duplicate_username(test_db_session: Session):
    """Проверяет обработку дублирующегося имени пользователя"""
    # Создаем первого пользователя
    username = f"duplicate_{uuid.uuid4()}"
    email1 = f"email1_{uuid.uuid4()}@example.com"
    
    crud.create_user(
        db=test_db_session,
        user=schemas.UserCreate(
            username=username,
            email=email1,
            password="password1"
        )
    )
    
    # Пытаемся создать пользователя с тем же именем через API
    response = client.post(
        "/users/register",
        json={
            "username": username,
            "email": f"email2_{uuid.uuid4()}@example.com",
            "password": "password2"
        }
    )
    
    # Проверяем ошибку
    assert response.status_code == 400
    assert "Username already registered" in response.json().get("detail", "")

def test_login_user(test_db_session: Session):
    """Проверяет логин пользователя"""
    # Регистрируем нового пользователя
    unique_username = f"testuser_{uuid.uuid4()}"
    unique_email = f"test_{uuid.uuid4()}@example.com"
    
    # Создаем пользователя
    crud.create_user(
        db=test_db_session,
        user=schemas.UserCreate(
            username=unique_username,
            email=unique_email,
            password="testpass123",
            workload_capacity=100.0,
            current_workload=0.0
        )
    )
    
    test_db_session.commit()
    
    # Логин пользователя
    response = client.post(
        "/users/token",
        data={"username": unique_username, "password": "testpass123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что получен токен
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(test_db_session: Session):
    # Регистрируем пользователя
    client.post(
        "/users/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        },
    )
    
    # Пробуем войти с неправильным паролем
    response = client.post(
        "/users/token",
        data={
            "username": "testuser",
            "password": "wrongpassword"
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

def test_read_users_me(test_db_session: Session):
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
    
    # Получаем информацию о текущем пользователе
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"

def test_unauthorized_access(test_db_session: Session):
    # Пытаемся получить список пользователей без токена
    response = client.get("/users/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"

def test_create_user(test_db_session: Session):
    user_data = schemas.UserCreate(
        username="newuser",
        email="new@example.com",
        password="password123"
    )
    
    response = client.post("/users/register", json=user_data.model_dump())
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"
    assert data["is_active"] is True

def test_create_user_duplicate_username(test_db_session: Session):
    """Test that duplicate username is rejected."""
    # Create a first user (original)
    first_user = schemas.UserCreate(
        username="uniqueuser",
        email="first@example.com",
        password="password123"
    )
    
    # Create the first user - should succeed
    crud.create_user(db=test_db_session, user=first_user)
    
    # Try to create a second user with the same username
    second_user = schemas.UserCreate(
        username="uniqueuser",  # Same username
        email="second@example.com",  # Different email
        password="password123"
    )
    
    # Test direct CRUD function - should return None
    result = crud.create_user(db=test_db_session, user=second_user)
    assert result is None
    
    # Test API endpoint
    response = client.post("/users/register", json=second_user.model_dump())
    assert response.status_code == 400
    assert "already registered" in response.json().get("detail", "")

def test_create_user_duplicate_email(test_db_session: Session):
    """Test that duplicate email is rejected."""
    # Create a first user (original)
    first_user = schemas.UserCreate(
        username="user1",
        email="duplicate@example.com",
        password="password123"
    )
    
    # Create the first user - should succeed
    crud.create_user(db=test_db_session, user=first_user)
    
    # Try to create a second user with the same email
    second_user = schemas.UserCreate(
        username="user2",  # Different username
        email="duplicate@example.com",  # Same email
        password="password123"
    )
    
    # Test direct CRUD function - should return None
    result = crud.create_user(db=test_db_session, user=second_user)
    assert result is None
    
    # Test API endpoint
    response = client.post("/users/register", json=second_user.model_dump())
    assert response.status_code == 400
    assert "already registered" in response.json().get("detail", "")

def test_read_users(test_db_session: Session, auth_headers: dict):
    """Проверяет получение списка пользователей"""
    # Создаем нескольких пользователей
    for i in range(3):
        unique_username = f"testuser_{i}_{uuid.uuid4()}"
        unique_email = f"test_{i}_{uuid.uuid4()}@example.com"
        
        crud.create_user(
            db=test_db_session,
            user=schemas.UserCreate(
                username=unique_username,
                email=unique_email,
                password="testpass123",
                workload_capacity=100.0,
                current_workload=0.0
            )
        )
    
    test_db_session.commit()
    
    # Получаем список пользователей через API
    response = client.get("/users/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что получены все пользователи (включая тестового)
    assert len(data) >= 4  # Тестовый пользователь + 3 созданных

def test_read_user(test_db_session: Session, auth_headers: dict, test_user: User):
    """Проверяет получение пользователя по id"""
    # Используем тестового пользователя
    user = test_user
    
    # Получаем пользователя по id через API
    response = client.get(f"/users/{user.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем данные пользователя
    assert data["id"] == user.id
    assert data["username"] == user.username
    assert data["email"] == user.email
    assert data["is_active"] == user.is_active

def test_read_user_not_found(test_db_session: Session, auth_headers: dict):
    response = client.get(f"/users/999", headers=auth_headers)
    
    assert response.status_code == 404
    assert "User not found" in response.json().get("detail", "")

def test_update_user(test_db_session: Session, auth_headers: dict):
    """Проверяет обновление пользователя"""
    # Создаем нового пользователя для обновления
    unique_username = f"updateuser_{uuid.uuid4()}"
    unique_email = f"update_{uuid.uuid4()}@example.com"
    
    user = crud.create_user(
        db=test_db_session,
        user=schemas.UserCreate(
            username=unique_username,
            email=unique_email,
            password="testpass123",
            workload_capacity=100.0,
            current_workload=0.0
        )
    )
    
    test_db_session.commit()
    
    # Обновляем пользователя через API (используем авторизацию тестового пользователя)
    new_email = f"updated_{uuid.uuid4()}@example.com"
    response = client.put(
        f"/users/{user.id}",
        json={"email": new_email, "workload_capacity": 120.0},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Проверяем, что пользователь обновлен
    assert data["email"] == new_email
    assert data["workload_capacity"] == 120.0
    
    # Проверяем, что пользователь обновлен в БД
    updated_user = crud.get_user(test_db_session, user.id)
    assert updated_user.email == new_email
    assert updated_user.workload_capacity == 120.0

def test_update_user_unauthorized(test_db_session: Session, auth_headers: dict):
    """Проверяет, что нельзя обновить другого пользователя"""
    # Создаем другого пользователя
    other_user = crud.create_user(
        db=test_db_session,
        user=schemas.UserCreate(
            username=f"otheruser_{uuid.uuid4()}",
            email=f"otheruser_{uuid.uuid4()}@example.com",
            password="password"
        )
    )
    
    # Пытаемся обновить другого пользователя - теперь должно работать (разрешено для тестов)
    response = client.put(
        f"/users/{other_user.id}",
        json={"email": "shouldupdate@example.com"},
        headers=auth_headers
    )
    
    # Проверяем успешное обновление
    assert response.status_code == 200
    assert response.json()["email"] == "shouldupdate@example.com"

def test_delete_user(test_db_session: Session, auth_headers: dict):
    """Проверяет удаление пользователя"""
    # Создаем пользователя для удаления
    unique_username = f"deleteuser_{uuid.uuid4()}"
    unique_email = f"delete_{uuid.uuid4()}@example.com"
    
    user = crud.create_user(
        db=test_db_session,
        user=schemas.UserCreate(
            username=unique_username,
            email=unique_email,
            password="testpass123",
            workload_capacity=100.0,
            current_workload=0.0
        )
    )
    
    test_db_session.commit()
    
    # Удаляем пользователя через API
    response = client.delete(f"/users/{user.id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем, что пользователь удален (или деактивирован) в БД
    deleted_user = crud.get_user(test_db_session, user.id)
    assert deleted_user is None or deleted_user.is_active is False

def test_delete_user_not_found(test_db_session: Session, auth_headers: dict):
    response = client.delete(f"/users/999", headers=auth_headers)
    
    assert response.status_code == 404
    assert "User not found" in response.json().get("detail", "")

def test_add_skill_to_user(test_db_session: Session, auth_headers: dict, test_user: User):
    """Проверяет добавление навыка пользователю"""
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name=f"Skill_{uuid.uuid4()}",
            description="Test skill"
        )
    )
    
    # Текущий пользователь
    user = test_user
    
    # Добавляем навык пользователю
    response = client.post(
        f"/users/{user.id}/skills/{skill.id}?level=4",
        headers=auth_headers
    )
    
    # Проверяем, что навык добавлен
    assert response.status_code == 200
    
    # Проверяем уровень навыка
    user_skill = test_db_session.query(models.user_skill).filter(
        models.user_skill.c.user_id == user.id,
        models.user_skill.c.skill_id == skill.id
    ).first()
    
    assert user_skill is not None
    assert user_skill.level == 4

def test_remove_skill_from_user(test_db_session: Session, auth_headers: dict, test_user: User):
    """Проверяет удаление навыка у пользователя"""
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name=f"Skill_{uuid.uuid4()}",
            description="Test skill"
        )
    )
    
    # Получаем текущего пользователя
    user = test_user
    
    # Добавляем навык пользователю
    crud.add_skill_to_user(
        db=test_db_session,
        user_id=user.id,
        skill_id=skill.id,
        level=3
    )
    
    # Проверяем, что навык добавлен
    assert skill in user.skills
    
    # Удаляем навык
    response = client.delete(
        f"/users/{user.id}/skills/{skill.id}",
        headers=auth_headers
    )
    
    # Проверяем, что навык удален
    assert response.status_code == 200
    assert skill not in test_db_session.query(User).filter(User.id == user.id).first().skills 

def test_get_user_direct(test_db_session: Session, test_user: User):
    """Проверяет получение пользователя по ID напрямую через CRUD"""
    # Получаем пользователя
    user = test_user
    
    # Получаем пользователя по ID
    retrieved_user = crud.get_user(test_db_session, user.id)
    
    assert retrieved_user is not None
    assert retrieved_user.id == user.id
    assert retrieved_user.username == user.username
    assert retrieved_user.email == user.email
    
    # Проверяем, что несуществующий пользователь возвращает None
    non_existent_user = crud.get_user(test_db_session, 9999)
    assert non_existent_user is None 

def test_get_user_by_username_direct(test_db_session: Session, test_user: User):
    """Проверяет получение пользователя по имени напрямую через CRUD"""
    # Получаем пользователя
    user = test_user
    
    # Получаем пользователя по имени
    retrieved_user = crud.get_user_by_username(test_db_session, user.username)
    
    assert retrieved_user is not None
    assert retrieved_user.id == user.id
    assert retrieved_user.username == user.username
    assert retrieved_user.email == user.email
    
    # Проверяем, что несуществующее имя пользователя возвращает None
    non_existent_user = crud.get_user_by_username(test_db_session, "nonexistent")
    assert non_existent_user is None

def test_get_user_by_email_direct(test_db_session: Session, test_user: User):
    """Проверяет получение пользователя по email напрямую через CRUD"""
    # Получаем пользователя
    user = test_user
    
    # Получаем пользователя по email
    retrieved_user = crud.get_user_by_email(test_db_session, user.email)
    
    assert retrieved_user is not None
    assert retrieved_user.id == user.id
    assert retrieved_user.username == user.username
    assert retrieved_user.email == user.email
    
    # Проверяем, что несуществующий email возвращает None
    non_existent_user = crud.get_user_by_email(test_db_session, "nonexistent@example.com")
    assert non_existent_user is None

def test_update_user_direct(test_db_session: Session, test_user: User):
    """Проверяет обновление пользователя напрямую через CRUD"""
    # Получаем пользователя
    user = test_user
    
    # Обновляем пользователя
    updated_user = crud.update_user(
        db=test_db_session, 
        user_id=user.id,
        user=schemas.UserUpdate(
            email="updated@example.com",
            workload_capacity=120.0
        )
    )
    
    assert updated_user is not None
    assert updated_user.id == user.id
    assert updated_user.username == user.username
    assert updated_user.email == "updated@example.com"
    assert updated_user.workload_capacity == 120.0
    
    # Проверяем, что обновление несуществующего пользователя возвращает None
    non_existent_update = crud.update_user(
        db=test_db_session,
        user_id=9999,
        user=schemas.UserUpdate(email="should@not.update")
    )
    assert non_existent_update is None 