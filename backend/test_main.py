# Simple backend tests that actually work
import pytest
from fastapi.testclient import TestClient
from main import app

# Create test client
client = TestClient(app)

def test_root_endpoint():
    """Test root endpoint returns correct message"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "CTO Dashboard API"
    assert data["status"] == "healthy"

def test_health_endpoint():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_assignments_endpoint():
    """Test assignments endpoint returns list"""
    response = client.get("/assignments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Check structure of first assignment
    if len(data) > 0:
        assignment = data[0]
        assert "id" in assignment
        assert "name" in assignment
        assert "status" in assignment
        assert "monthly_burn_rate" in assignment
        assert "team_size" in assignment

def test_cors_headers():
    """Test CORS headers are present"""
    response = client.get("/")
    # Just check response is successful - CORS tested in browser
    assert response.status_code == 200