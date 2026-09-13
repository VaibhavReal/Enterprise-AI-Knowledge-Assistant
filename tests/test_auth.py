def test_register(client):
    response = client.post("/auth/register", json={
        "email": "newuser@example.com",
        "password": "securepassword",
        "full_name": "New User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "password" not in data

def test_register_duplicate_email(client, test_user_data):
    client.post("/auth/register", json=test_user_data)
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == 400

def test_login_success(client, test_user_data):
    client.post("/auth/register", json=test_user_data)
    response = client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"]
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_wrong_password(client, test_user_data):
    client.post("/auth/register", json=test_user_data)
    response = client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_login_unknown_email(client):
    response = client.post("/auth/login", json={
        "email": "unknown@example.com",
        "password": "password"
    })
    assert response.status_code == 401

def test_protected_endpoint_valid_token(client, auth_headers):
    response = client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_protected_endpoint_without_token(client):
    response = client.get("/users/me")
    assert response.status_code == 401

def test_protected_endpoint_invalid_token(client):
    response = client.get("/users/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401
