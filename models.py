from datetime import datetime  # used for timestamps (e.g. reward unlock time)
from pydantic import BaseModel  # used for request validation schemas
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String  # SQL column types
from sqlalchemy.orm import relationship  # ORM relationships between tables

from database import Base  # base class for all models


# USER TABLE
class User(Base):
    __tablename__ = "users"  # table name in database

    id = Column(Integer, primary_key=True, index=True)  # unique user ID
    email = Column(String, unique=True, nullable=False)  # user email

    password = Column(String, nullable=True)  # deprecated (Firebase handles auth now)

    firebase_uid = Column(String, unique=True, nullable=True, index=True)  # Firebase user ID

    # relationships to other tables
    expenses = relationship("Expense", back_populates="user", cascade="all, delete")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete")
    goals = relationship("Goal", back_populates="user", cascade="all, delete")
    fixed_expenses = relationship("FixedExpense", back_populates="user", cascade="all, delete")
    rewards = relationship("UserReward", back_populates="user", cascade="all, delete")


# CATEGORY TABLE
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)  # unique category ID
    name = Column(String, unique=True, nullable=False)  # category name

    # relationships
    expenses = relationship("Expense", back_populates="category")
    goals = relationship("Goal", back_populates="category")


# EXPENSE TABLE
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)  # unique expense ID

    user_id = Column(Integer, ForeignKey("users.id"))  # link to user
    amount = Column(Integer)  # amount spent

    category_id = Column(Integer, ForeignKey("categories.id"))  # link to category
    date = Column(Date)  # date of expense

    receipt_url = Column(String, nullable=True)  # optional receipt image

    type = Column(String)   # type of expense (essential or optional)

    # relationships
    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")


# BUDGET TABLE
class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)  # unique budget ID

    user_id = Column(Integer, ForeignKey("users.id"))  # link to user

    month = Column(String, nullable=True)  # format YYYY-MM
    income = Column(Integer)  # total income
    allowance = Column(Integer, nullable=True)  # allowed spending

    # relationship
    user = relationship("User", back_populates="budgets")


# GOAL TABLE
class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)  # unique goal ID

    user_id = Column(Integer, ForeignKey("users.id"))  # link to user
    category_id = Column(Integer, ForeignKey("categories.id"))  # category being tracked

    limit_amount = Column(Integer)  # spending limit
    month = Column(String, nullable=True)  # goal month

    status = Column(String)  # goal status: in_progress, completed, failed

    # relationships
    user = relationship("User", back_populates="goals")
    category = relationship("Category", back_populates="goals")


# FIXED EXPENSE TABLE
class FixedExpense(Base):
    __tablename__ = "fixed_expenses"

    id = Column(Integer, primary_key=True, index=True)  # unique fixed expense ID

    user_id = Column(Integer, ForeignKey("users.id"))  # link to user

    name = Column(String)  # name of expense (e.g. rent)
    amount = Column(Integer)  # fixed amount

    # relationship
    user = relationship("User", back_populates="fixed_expenses")


# REWARD TABLE
class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)  # reward ID

    name = Column(String)  # reward name
    description = Column(String)  # reward description

    # relationship to users via UserReward
    users = relationship("UserReward", back_populates="reward")


# USER REWARD TABLE (JOIN TABLE)
class UserReward(Base):
    __tablename__ = "user_rewards"

    id = Column(Integer, primary_key=True, index=True)  # unique ID

    user_id = Column(Integer, ForeignKey("users.id"))  # link to user
    reward_id = Column(Integer, ForeignKey("rewards.id"))  # link to reward

    unlocked_at = Column(DateTime, default=datetime.utcnow)  # timestamp when unlocked

    # relationships
    user = relationship("User", back_populates="rewards")
    reward = relationship("Reward", back_populates="users")


# REQUEST SCHEMA FOR BUDGET
class BudgetRequest(BaseModel):
    income: int  # user's income
    allowance: int  # allowed spending


# REQUEST SCHEMA FOR EXPENSE
class ExpenseRequest(BaseModel):
    amount: int  # expense amount
    category_name: str  # category name (string, not ID)
    date: str  # date in string format
    type: str  # essential or optional