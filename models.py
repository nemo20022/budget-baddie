from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


# 👤 USER
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False)

    password = Column(String, nullable=True)  # deprecated (Firebase auth)

    firebase_uid = Column(String, unique=True, nullable=True, index=True)

    expenses = relationship("Expense", back_populates="user", cascade="all, delete")
    budgets = relationship("Budget", back_populates="user", cascade="all, delete")
    goals = relationship("Goal", back_populates="user", cascade="all, delete")
    fixed_expenses = relationship("FixedExpense", back_populates="user", cascade="all, delete")
    rewards = relationship("UserReward", back_populates="user", cascade="all, delete")


# 🏷 CATEGORY
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    expenses = relationship("Expense", back_populates="category")
    goals = relationship("Goal", back_populates="category")

# 💸 EXPENSE
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Integer)

    category_id = Column(Integer, ForeignKey("categories.id"))
    date = Column(Date)

    receipt_url = Column(String, nullable=True)

    type = Column(String)   # ✅ ADD THIS LINE

    user = relationship("User", back_populates="expenses")
    category = relationship("Category", back_populates="expenses")

# 💰 BUDGET
class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    month = Column(String, nullable=True)  # later enforce YYYY-MM
    income = Column(Integer)
    allowance = Column(Integer, nullable=True)

    user = relationship("User", back_populates="budgets")


# 🎯 GOAL
class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))

    limit_amount = Column(Integer)
    month = Column(String, nullable=True)

    status = Column(String)  # "in_progress", "completed", "failed"

    user = relationship("User", back_populates="goals")
    category = relationship("Category", back_populates="goals")


# 🧾 FIXED EXPENSE
class FixedExpense(Base):
    __tablename__ = "fixed_expenses"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    name = Column(String)
    amount = Column(Integer)

    user = relationship("User", back_populates="fixed_expenses")


# 🏆 REWARD
class Reward(Base):
    __tablename__ = "rewards"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)
    description = Column(String)

    users = relationship("UserReward", back_populates="reward")


# 🎁 USER REWARD
class UserReward(Base):
    __tablename__ = "user_rewards"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    reward_id = Column(Integer, ForeignKey("rewards.id"))

    unlocked_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="rewards")
    reward = relationship("Reward", back_populates="users")
    
class BudgetRequest(BaseModel):
    income: int
    allowance: int
    
class ExpenseRequest(BaseModel):
    amount: int
    category_name: str
    date: str
    type: str