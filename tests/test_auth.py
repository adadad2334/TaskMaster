import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import jwt
from datetime import datetime, timedelta

from app.main import app as fastapi_app
from app.models import User
from app import crud, schemas
from app.auth import get_password_hash, verify_password, create_access_token
from app.auth import SECRET_KEY, ALGORITHM
from .conftest import test_db_session, client, test_user

def test_auth_flow(test_db_session: Session, test_user: User):
    """Test the full auth flow - login and access protected endpoint"""
    # First try direct login
    login_response = client.post(
        "/users/token",
        data={"username": "testuser", "password": "password"}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    
    # Try accessing a protected endpoint
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    user_data = response.json()
    assert user_data["username"] == "testuser"
    
    # Try getting all users with the same token
    users_response = client.get("/users/", headers=headers)
    assert users_response.status_code == 200 

def test_password_hash_and_verify():
    """Test the password hashing and verification functions"""
    password = "test_password123"
    
    # Hash the password
    hashed_password = get_password_hash(password)
    
    # Verify that the hashed password is not the plain password
    assert hashed_password != password
    
    # Verify that the password verification works
    assert verify_password(password, hashed_password) is True
    
    # Verify that an incorrect password doesn't verify
    assert verify_password("wrong_password", hashed_password) is False

def test_create_access_token():
    """Test creating a JWT access token"""
    # Create a token
    data = {"sub": "testuser"}
    token = create_access_token(data)
    
    # Verify that the token is a string and not empty
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Verify that we can decode the token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "testuser"
    assert "exp" in payload  # Verify the expiration is set 