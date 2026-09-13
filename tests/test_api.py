def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register_creates_user(client):
    response = client.post("/auth/register", json={
        "email": "apiuser@example.com",
        "password": "apipassword",
        "full_name": "API User"
    })
    assert response.status_code == 201

def test_login_returns_token(client):
    client.post("/auth/register", json={
        "email": "loginuser@example.com",
        "password": "loginpassword",
        "full_name": "Login User"
    })
    response = client.post("/auth/login", json={
        "email": "loginuser@example.com",
        "password": "loginpassword"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_get_documents_requires_auth(client):
    response = client.get("/documents/")
    assert response.status_code == 401

def test_get_chats_requires_auth(client):
    response = client.get("/chats/")
    assert response.status_code == 401

def test_create_chat(client, auth_headers):
    response = client.post("/chats/", headers=auth_headers, json={"title": "New Chat", "document_ids": []})
    assert response.status_code == 201
    assert "id" in response.json()
    assert response.json()["title"] == "New Chat"
