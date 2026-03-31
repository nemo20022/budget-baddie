# Budget Baddie 💰

A gamified budgeting app that helps users track spending, stay within budget, and analyze financial habits in real time.

---

## Live Demo

Frontend: https://budget-baddie-frontend.vercel.app
Backend API: https://budget-baddie-production.up.railway.app

---

## Features

* Firebase Authentication (Login / Signup)
* User sync with backend database
* Expense tracking (essential vs optional)
* Monthly budget system
* Real-time budget calculations
* Category-based analytics
* Monthly spending comparison (this month vs last month)
* Smart insights (top spending category detection)
* Goals and rewards system

---

## Tech Stack

### Backend

* FastAPI
* SQLAlchemy
* SQLite (local development)
* PostgreSQL (production via Railway)

### Frontend

* HTML, CSS, JavaScript
* Fetch API

### Auth

* Firebase Authentication

---

## How to Run

### 1. Start backend

uvicorn main:app --reload

Backend runs at:

http://127.0.0.1:8000

---

### 2. Open frontend

Open in browser:

login.html

---

## Authentication Flow

1. User logs in via Firebase
2. Frontend receives JWT token
3. Token is sent with each API request
4. Backend verifies token using Firebase Admin SDK
5. User is synced to database (/users/sync)

---

## Project Structure

/project
├── main.py
├── models.py
├── database.py
├── budget.db
├── login.html
├── app.html
├── login.css
├── app.css

---

## Key Endpoints

POST   /users/sync        → Sync Firebase user
POST   /budget            → Create/update budget
GET    /budget/remaining  → Get current budget stats
POST   /expenses          → Add expense
GET    /expenses          → Get user expenses
GET    /insights/monthly  → Monthly insights

---

## Important Details

* All endpoints require a valid Firebase token
* Budget is stored per month
* Expenses are categorized and typed (essential / optional)
* Monthly insights are calculated dynamically from expense data
* Frontend handles UI updates and error display

---

## Status

* Fully working full-stack application
* Deployed and live
* Ready for UI improvements and advanced analytics

---

## Future Improvements

* More advanced charts and visual analytics
* Improved UX feedback (toasts, loaders)
* Recurring expenses
* Data export (CSV / reports)
