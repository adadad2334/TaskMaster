import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_app_root():
    """Test the root endpoint of the application"""
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to Task Assignment API" in response.json()["message"]
    
def test_app_includes_routers():
    """Test that the app has proper routers attached"""
    # Get all routes from the app
    routes = app.routes
    
    # Extract route paths
    paths = [route.path for route in routes if hasattr(route, 'path')]
    
    # Check that important API routes are included
    assert "/users/" in paths
    assert "/projects/" in paths
    assert "/tasks/" in paths
    assert "/skills/" in paths 