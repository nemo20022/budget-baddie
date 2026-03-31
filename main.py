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
import os
import json
import firebase_admin
from firebase_admin import credentials, auth
from sqlalchemy import extract, func
firebase_key = os.getenv("FIREBASE_KEY")

if firebase_key:
    cred_dict = json.loads(firebase_key)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

security = HTTPBearer()

# ✅ TOKEN VERIFY (unchanged)
def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    if not firebase_admin._apps:
        raise HTTPException(
            status_code=500,
            detail="Firebase not initialized",
        )

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
        month=datetime.now().strftime("%Y-%m"),  # ✅ ADD THIS
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

@app.get("/goals/check")
def check_goal(user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    goals = db.query(Goal).filter(Goal.user_id == db_user.id).all()

    results = []

    for goal in goals:
        expenses = db.query(Expense).filter(
            Expense.user_id == db_user.id,
            Expense.category_id == goal.category_id
        ).all()

        total_spent = sum(exp.amount for exp in expenses)

        if total_spent <= goal.limit_amount:
            goal.status = "completed"   # ✅ THIS IS THE CRITICAL LINE
            db.commit()
            status = "Goal achieved"
        else:
            goal.status = "failed"
            db.commit()
            status = "Goal exceeded"

        results.append({
            "category_id": goal.category_id,
            "limit": goal.limit_amount,
            "spent": total_spent,
            "status": status
        })

    return results

@app.get("/rewards")
def get_stage(user=Depends(verify_token), db=Depends(get_db)):
    firebase_uid = user["uid"]

    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        return {"error": "User not found"}

    # count completed goals
    completed_goals = db.query(Goal).filter(
        Goal.user_id == db_user.id,
        Goal.status == "completed"
    ).count()

    # stage system (max 5)
    stage = min(completed_goals, 5)
    
    return {
        "stage": stage,
        "completed_goals": completed_goals
    }
    
@app.get("/stats/summary")
def monthly_summary(user=Depends(verify_token), db=Depends(get_db)):
    from datetime import datetime

    firebase_uid = user["uid"]
    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    now = datetime.now()
    this_month = now.month
    this_year = now.year

    last_month = this_month - 1 if this_month > 1 else 12
    last_month_year = this_year if this_month > 1 else this_year - 1

    expenses = db.query(Expense).filter(Expense.user_id == db_user.id).all()

    this_total = sum(
        e.amount for e in expenses
        if e.date.month == this_month and e.date.year == this_year
    )

    last_total = sum(
        e.amount for e in expenses
        if e.date.month == last_month and e.date.year == last_month_year
    )

    difference = last_total - this_total

    return {
        "this_month": this_total,
        "last_month": last_total,
        "difference": difference,
        "message": (
            f"You saved {difference} 🎉"
            if difference > 0
            else f"You spent {abs(difference)} more 💸"
        )
    }
    
    
@app.get("/insights/monthly")
def get_monthly_insights(
    user=Depends(verify_token),
    db=Depends(get_db)
):
    # ✅ get firebase uid
    firebase_uid = user["uid"]

    # ✅ get actual DB user
    db_user = db.query(User).filter(User.firebase_uid == firebase_uid).first()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    now = datetime.now()

    this_month = now.month
    this_year = now.year

    last_month = this_month - 1 if this_month > 1 else 12
    last_year = this_year if this_month > 1 else this_year - 1

    # ✅ THIS MONTH TOTAL
    this_total = db.query(func.sum(Expense.amount)).filter(
        Expense.user_id == db_user.id,
        extract('month', Expense.date) == this_month,
        extract('year', Expense.date) == this_year
    ).scalar() or 0

    # ✅ LAST MONTH TOTAL
    last_total = db.query(func.sum(Expense.amount)).filter(
        Expense.user_id == db_user.id,
        extract('month', Expense.date) == last_month,
        extract('year', Expense.date) == last_year
    ).scalar() or 0

    # ✅ TOP CATEGORY (FIXED WITH JOIN)
    top_category = db.query(
        Category.name,
        func.sum(Expense.amount).label("total")
    ).join(
        Category, Expense.category_id == Category.id
    ).filter(
        Expense.user_id == db_user.id,
        extract('month', Expense.date) == this_month,
        extract('year', Expense.date) == this_year
    ).group_by(
        Category.name
    ).order_by(
        func.sum(Expense.amount).desc()
    ).first()

    return {
        "this_month": this_total,
        "last_month": last_total,
        "top_category": top_category[0] if top_category else None
    }