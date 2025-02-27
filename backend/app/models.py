from sqlalchemy import Column, Integer, Float, String, Date, Boolean
from sqlalchemy.ext.declarative import declarative_base
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    active = Column(Boolean, default=True)

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date)
    description = Column(String)
    amount = Column(Float)
    paid_by = Column(String, default="Split")  # Default to "Split"
    category = Column(String, nullable=True)  # Optional category field