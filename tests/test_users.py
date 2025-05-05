import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User

# Создаем тестовую базу данных в памяти
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Переопределяем зависимость get_db для тестов
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Создаем тестовый клиент
client = TestClient(app)

@pytest.fixture(scope="function")
def test_db():
    # Создаем таблицы перед каждым тестом
    Base.metadata.create_all(bind=engine)
    yield
    # Удаляем таблицы после каждого теста
    Base.metadata.drop_all(bind=engine)

def test_register_user(test_db):
    # Регистрируем пользователя
    response = client.post(
        "/users/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "workload_capacity": 100.0
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data

def test_register_duplicate_username(test_db):
    # Регистрируем первого пользователя
    client.post(
        "/users/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        },
    )
    
    # Пытаемся зарегистрировать пользователя с тем же именем
    response = client.post(
        "/users/register",
        json={
            "username": "testuser",
            "email": "another@example.com",
            "password": "password123"
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Username already registered"

def test_login_user(test_db):
    # Регистрируем пользователя
    client.post(
        "/users/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123"
        },
    )
    
    # Пробуем войти
    response = client.post(
        "/users/token",
        data={
            "username": "testuser",
            "password": "password123"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(test_db):
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

def test_read_users_me(test_db):
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

def test_unauthorized_access(test_db):
    # Пытаемся получить список пользователей без токена
    response = client.get("/users/")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated" 