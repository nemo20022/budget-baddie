from fastapi import FastAPI
from database import engine
import models
from database import SessionLocal
from models import User
from models import Expense
from datetime import datetime
from models import Budget
from models import Goal
from models import Category
from models import ExpenseRequest
from models import Reward, UserReward
from models import BudgetRequest
from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status

import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("budget-baddie-firebase-adminsdk-fbsvc-7dbf5e87f3.json")
firebase_admin.initialize_app(cred)

security = HTTPBearer()

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)



@app.post("/users")
def create_user(email: str, password: str):
    db=SessionLocal()

    new_user = User(email=email, password=password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message":"User created","user_id":new_user.id}

@app.post("/users/sync")
def sync_user(user=Depends(verify_token)):
    db = SessionLocal()

    firebase_uid = user["uid"]
    email = user.get("email")

    existing = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if existing:
        return {"message": "User already exists"}

    new_user = User(
        email=email,
        password="firebase_auth",
        firebase_uid=firebase_uid
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User synced", "user_id": new_user.id}

@app.get("/users")
def get_users():
    db=SessionLocal()

    users=db.query(User).all()

    return users

@app.post("/expenses")
def create_expense(data: ExpenseRequest, user=Depends(verify_token)):
    db = SessionLocal()

    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    # find or create category
    category = db.query(Category).filter(Category.name == data.category_name).first()

    if not category:
        category = Category(name=data.category_name)
        db.add(category)
        db.commit()
        db.refresh(category)

    expense_date = datetime.strptime(data.date, "%Y-%m-%d")

    new_expense = Expense(
        user_id=db_user.id,
        amount=data.amount,
        category_id=category.id,
        date=expense_date
    )

    db.add(new_expense)
    db.commit()

    return {"message": "Expense added"}


@app.get("/expenses")
def get_expenses(user_id: int):
    db=SessionLocal()

    expenses=db.query(Expense).filter(Expense.user_id == user_id).all()

    return expenses


@app.get("/stats/total")
def get_total_spending(user_id: int):
    db =SessionLocal()

    expenses=db.query(Expense).filter(Expense.user_id == user_id).all()

    total =0
    for expense in expenses:
        total += expense.amount

    return {"user_id":user_id,"total_spent": total}


@app.get("/stats/category")
def get_category_stats(user_id: int):
    db = SessionLocal()

    results = (
        db.query(Category.name, Expense.amount)
        .join(Expense, Expense.category_id == Category.id)
        .filter(Expense.user_id == user_id)
        .all()
    )

    category_totals = {}

    for name, amount in results:
        if name in category_totals:
            category_totals[name] += amount
        else:
            category_totals[name] = amount

    return category_totals

@app.get("/stats/month-comparison")
def month_comparison(user_id: int):
    db = SessionLocal()

    expenses = db.query(Expense).filter(Expense.user_id == user_id).all()

    now = datetime.now()
    current_month = now.month
    current_year = now.year

    last_month = current_month - 1
    last_month_year = current_year

    if last_month == 0:
        last_month = 12
        last_month_year -= 1

    current_total = 0
    last_total = 0

    for expense in expenses:
        expense_date = expense.date   # already a date object

        if expense_date.month == current_month and expense_date.year == current_year:
            current_total += expense.amount

        elif expense_date.month == last_month and expense_date.year == last_month_year:
            last_total += expense.amount

    difference = current_total - last_total

    return {
        "current_month": current_total,
        "last_month": last_total,
        "difference": difference
    }

@app.post("/budget")
def set_budget(data: BudgetRequest, user=Depends(verify_token)):
    db = SessionLocal()

    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    new_budget = Budget(
        user_id=db_user.id,
        income=data.income
    )

    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)

    return {"message": "Budget set"}

@app.get("/budget/remaining")
def get_remaining_budget(user=Depends(verify_token)):
    db = SessionLocal()

    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    # get latest budget
    budget = (
        db.query(Budget)
        .filter(Budget.user_id == db_user.id)
        .order_by(Budget.id.desc())
        .first()
    )

    if not budget:
        return {"error": "No budget found"}

    expenses = db.query(Expense).filter(Expense.user_id == db_user.id).all()

    total_spent = sum(exp.amount for exp in expenses)

    remaining = budget.income - total_spent

    return {
        "income": budget.income,
        "total_spent": total_spent,
        "remaining": remaining
    }

@app.get("/expenses")
def get_expenses(user=Depends(verify_token)):
    db = SessionLocal()

    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    expenses = db.query(Expense).filter(Expense.user_id == db_user.id).all()

    return expenses

@app.post("/goals")
def create_goal(user_id: int, category_name: str, limit_amount: int):
    db = SessionLocal()

    # find category
    category = db.query(Category).filter(Category.name == category_name).first()

    if not category:
        return {"error": "Category not found"}

    new_goal = Goal(
        user_id=user_id,
        category_id=category.id,
        limit_amount=limit_amount,
        status="in_progress"
    )

    db.add(new_goal)
    db.commit()
    db.refresh(new_goal)

    return {"message": "Goal created", "goal_id": new_goal.id}

@app.get("/goals/check")
def check_goal(user_id: int, category_name: str):
    db = SessionLocal()

    # find category
    category = db.query(Category).filter(Category.name == category_name).first()

    if not category:
        return {"error": "Category not found"}

    # get goal
    goal = db.query(Goal).filter(
        Goal.user_id == user_id,
        Goal.category_id == category.id
    ).first()

    if not goal:
        return {"error": "No goal found"}

    # get expenses
    expenses = db.query(Expense).filter(
        Expense.user_id == user_id,
        Expense.category_id == category.id
    ).all()

    total_spent = sum(exp.amount for exp in expenses)

    if total_spent <= goal.limit_amount:
        status = "Goal achieved"

        reward = db.query(Reward).first()

        if not reward:
            reward = Reward(
                name="Savings Star",
                description="You stayed within your budget!"
            )
            db.add(reward)
            db.commit()
            db.refresh(reward)

        existing = db.query(UserReward).filter(
            UserReward.user_id == user_id,
            UserReward.reward_id == reward.id
        ).first()

        if not existing:
            user_reward = UserReward(
                user_id=user_id,
                reward_id=reward.id
            )
            db.add(user_reward)
            db.commit()

    else:
        status = "Goal exceeded"

    return {
        "category": category.name,
        "limit": goal.limit_amount,
        "spent": total_spent,
        "status": status
    }


