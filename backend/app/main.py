import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router
from database import engine, Base  # Import your database connection and Base
import models

DATABASE_PATH = "expenses.db"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    yield
    # Code to run on shutdown
    engine.dispose()  # Close all connections

app = FastAPI(lifespan=lifespan)

# Enable CORS to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow requests from React
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(router)

@app.get("/")
def home():
    return {"message": "Expense Tracker API is running!"}
