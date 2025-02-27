from sqlalchemy import Column, Integer, String, Float
from .database import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    description = Column(String)
    amount = Column(Float)
    paid_by = Column(String)
