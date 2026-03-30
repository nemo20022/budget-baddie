from fastapi import FastAPI
from database import engine
import models
from database import SessionLocal
from models import User, Expense, Budget, Goal, Category, Reward, UserReward
from models import ExpenseRequest, BudgetRequest
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import requests
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status

import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("budget-baddie-firebase-adminsdk-fbsvc-7dbf5e87f3.json")
firebase_admin.initialize_app(cred)

security = HTTPBearer()

# ✅ TOKEN VERIFY (unchanged)
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

# ✅ DB DEPENDENCY (NEW)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

models.Base.metadata.create_all(bind=engine)

# ---------------- USERS ----------------

@app.post("/users")
def create_user(email: str, password: str, db=Depends(get_db)):
    new_user = User(email=email, password=password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User created", "user_id": new_user.id}


@app.post("/users/sync")
def sync_user(user=Depends(verify_token), db=Depends(get_db)):
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
def get_users(db=Depends(get_db)):
    return db.query(User).all()

# ---------------- EXPENSES ----------------

@app.post("/expenses")
def create_expense(data: ExpenseRequest, user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    category = db.query(Category).filter(Category.name == data.category_name).first()

    if not category:
        category = Category(name=data.category_name)
        db.add(category)
        db.commit()
        db.refresh(category)

    expense_date = datetime.strptime(data.date, "%Y-%m-%d").date()

    new_expense = Expense(
        user_id=db_user.id,
        amount=data.amount,
        category_id=category.id,
        date=expense_date,
        type=data.type
    )

    db.add(new_expense)
    db.commit()

    return {"message": "Expense added"}

# ---------------- STATS ----------------

@app.get("/stats/total")
def get_total_spending(user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]
    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    expenses = db.query(Expense).filter(Expense.user_id == db_user.id).all()
    total = sum(exp.amount for exp in expenses)

    return {"total_spent": total}


@app.get("/stats/category")
def get_category_stats(user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]
    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    results = (
        db.query(Category.name, Expense.amount)
        .join(Expense, Expense.category_id == Category.id)
        .filter(Expense.user_id == db_user.id)
        .all()
    )

    category_totals = {}

    for name, amount in results:
        category_totals[name] = category_totals.get(name, 0) + amount

    return category_totals

# ---------------- BUDGET ----------------

@app.post("/budget")
def set_budget(data: BudgetRequest, user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    current_month = datetime.now().strftime("%Y-%m")

    existing_budget = db.query(Budget).filter(
        Budget.user_id == db_user.id,
        Budget.month == current_month
    ).first()

    if existing_budget:
        existing_budget.income = data.income
        existing_budget.allowance = data.allowance
        db.commit()
        return {"message": "Budget updated"}

    else:
        new_budget = Budget(
            user_id=db_user.id,
            income=data.income,
            allowance=data.allowance,
            month=current_month
        )
        db.add(new_budget)
        db.commit()
        db.refresh(new_budget)

        return {"message": "Budget created"}


@app.get("/budget/remaining")
def get_remaining_budget(user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    current_month = datetime.now().strftime("%Y-%m")

    budget = db.query(Budget).filter(
        Budget.user_id == db_user.id,
        Budget.month == current_month
    ).first()

    if not budget:
        return {"error": "No budget found"}

    now = datetime.now()

    expenses = db.query(Expense).filter(
        Expense.user_id == db_user.id
    ).all()

    expenses = [
        e for e in expenses
        if e.date.month == now.month and e.date.year == now.year
    ]

    essential_spent = sum(e.amount for e in expenses if e.type == "essential")
    optional_spent  = sum(e.amount for e in expenses if e.type == "optional")

    available_money = budget.income - essential_spent

    allowance = budget.allowance or 0
    remaining = allowance - optional_spent

    return {
        "income": budget.income,
        "budget": allowance,
        "essential_spent": essential_spent,
        "optional_spent": optional_spent,
        "available": available_money,
        "remaining": remaining
    }

# ---------------- EXPENSE LIST ----------------

@app.get("/expenses")
def get_expenses(user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    return db.query(Expense).filter(Expense.user_id == db_user.id).all()

# ---------------- GOALS ----------------

@app.post("/goals")
def create_goal(category_name: str, limit_amount: int, user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]
    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    category = db.query(Category).filter(Category.name == category_name).first()

    if not category:
        return {"error": "Category not found"}

    new_goal = Goal(
        user_id=db_user.id,
        category_id=category.id,
        limit_amount=limit_amount,
        status="in_progress"
    )

    db.add(new_goal)
    db.commit()

    return {"message": "Goal created"}

@app.get("/quote")
def get_quote():
    try:
        res = requests.get("https://zenquotes.io/api/random")
        data = res.json()[0]

        return {
            "quote": data["q"],
            "author": data["a"]
        }
    except:
        return {
            "quote": "Stay consistent, your future self is watching 👀",
            "author": "Budget Baddie"
        }