import os

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.routes import router
from app.database import engine, Base  # Import your database connection and Base
from app import models

DATABASE_PATH = "expenses.db"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    # Ensure database tables are created on startup
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    yield
    # Code to run on shutdown
    engine.dispose()  # Close all connections
    
    # Delete the database file on shutdown
    #if os.path.exists(DATABASE_PATH):
    #    os.remove(DATABASE_PATH)
    #    print(f"Database {DATABASE_PATH} deleted")

app = FastAPI(lifespan=lifespan)

app.include_router(router)

@app.get("/")
def home():
    return {"message": "Expense Tracker API is running!"}