# FastAPI SQLite Backend

This is a simple backend API built using FastAPI, SQLite, and SQLAlchemy. It serves as a basic template to help you get started with building APIs with FastAPI and managing data with SQLAlchemy.

## Installation
- Install dependencies
```bash
pip install -r requirements.txt
``` 

## Usage
- To start the FastAPI server, run the following command in the folder backend/app/:
```bash
uvicorn app.main:app --reload
```
--reload enables auto-reloading of the server during development.
- The server will be running at http://127.0.0.1:8000.

## Development
For local development, you can edit and update any of the following files:

- app/crud.py: Contains the logic for interacting with the database.
- app/models.py: Defines the database models (tables).
- app/schemas.py: Defines the Pydantic schemas for request and response validation.
- app/routes.py: Defines the API routes and endpoints.
- app/database.py: Manages the database connection and session.