# API Documentation

This document outlines the REST API endpoints for the Financial Research Assistant.

## Authentication Endpoints

### `POST /auth/register`
*   **Description**: Creates a new user account.
*   **Auth Required**: No
*   **Request Body**:
    ```json
    {
      "email": "user@example.com",
      "password": "securepassword123",
      "full_name": "Jane Doe"
    }
    ```
*   **Response (201 Created)**: User object (excluding password).
*   **Errors**: 400 (Email already registered).

### `POST /auth/login`
*   **Description**: Authenticates a user and returns a JWT token. Uses OAuth2 Password Flow.
*   **Auth Required**: No
*   **Request Body (Form Data)**: `username` (email) and `password`.
*   **Response (200 OK)**:
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR...",
      "token_type": "bearer"
    }
    ```
*   **Errors**: 401 (Incorrect email or password).

---

## User Endpoints

### `GET /users/me`
*   **Description**: Retrieves the currently authenticated user's profile.
*   **Auth Required**: Yes (Bearer Token)
*   **Response (200 OK)**: User object.

---

## Document Endpoints

### `POST /documents/upload`
*   **Description**: Uploads a document (PDF, TXT) and begins the ingestion process (chunking, embedding).
*   **Auth Required**: Yes
*   **Request Body**: `multipart/form-data` with a `file` field.
*   **Response (202 Accepted)**:
    ```json
    {
      "id": 1,
      "filename": "annual_report.pdf",
      "status": "processing"
    }
    ```

### `GET /documents/`
*   **Description**: Lists all documents uploaded by the user.
*   **Auth Required**: Yes
*   **Response (200 OK)**: Array of document objects.

### `GET /documents/{id}`
*   **Description**: Retrieves status and details of a specific document.
*   **Auth Required**: Yes
*   **Response (200 OK)**: Document object.

### `DELETE /documents/{id}`
*   **Description**: Deletes a document and all its associated vector chunks.
*   **Auth Required**: Yes
*   **Response (204 No Content)**.

---

## Chat Endpoints

### `POST /chats/`
*   **Description**: Creates a new chat session.
*   **Auth Required**: Yes
*   **Request Body**:
    ```json
    {
      "title": "Q3 Earnings Analysis",
      "document_ids": [1, 2] // Optional: Restrict search to specific docs
    }
    ```
*   **Response (201 Created)**: Chat object.

### `GET /chats/`
*   **Description**: Lists all chat sessions for the user.
*   **Auth Required**: Yes
*   **Response (200 OK)**: Array of chat objects.

### `GET /chats/{id}/messages`
*   **Description**: Retrieves the message history for a specific chat.
*   **Auth Required**: Yes
*   **Response (200 OK)**: Array of message objects.

### `POST /chats/{id}/messages` (Server-Sent Events)
*   **Description**: Sends a query to the RAG pipeline and streams the LLM response back.
*   **Auth Required**: Yes
*   **Request Body**:
    ```json
    {
      "content": "What was the revenue for FY24?"
    }
    ```
*   **Response Format**: text/event-stream
    The server pushes events in the following format:
    ```text
    event: chunk
    data: {"text": "The "}

    event: chunk
    data: {"text": "revenue "}
    
    ...

    event: sources
    data: [{"document_id": 1, "page": 5, "text_preview": "..."}]

    event: end
    data: {}
    ```
*   **Errors**: 404 (Chat not found).
---

## System

### `GET /health`
*   **Description**: Basic health check.
*   **Auth Required**: No
*   **Response (200 OK)**: `{"status": "healthy"}`
