# Budget Baddie 💰

A full-stack personal finance tracker with authentication, budgeting, and expense analytics.

---

## ✨ Features

* 🔐 Firebase Authentication (Login / Signup)
* 👤 User sync with backend database
* 💸 Expense tracking (essential vs optional)
* 💰 Monthly budget system
* 📊 Real-time budget calculations
* 📈 Category-based analytics
* 📅 Monthly spending comparison
* 🎯 Goals & rewards system

---

## 🧠 Tech Stack

### Backend

* FastAPI
* SQLAlchemy
* SQLite

### Frontend

* HTML, CSS, JavaScript
* Fetch API

### Auth

* Firebase Authentication

---

## 🚀 How to Run

### 1. Start backend

```bash
uvicorn main:app --reload
```

Backend runs at:

```
http://127.0.0.1:8000
```

---

### 2. Open frontend

Open in browser:

```
login.html
```

---

## 🔐 Authentication Flow

1. User logs in via Firebase
2. Frontend gets JWT token
3. Token is sent to backend
4. Backend verifies token
5. User is synced to database (`/users/sync`)

---

## 📂 Project Structure

```
/project
  ├── main.py
  ├── models.py
  ├── database.py
  ├── budget.db
  ├── login.html
  ├── app.html
  ├── login.css
  ├── app.css
```

---

## ⚙️ Key Endpoints

| Method | Endpoint          | Description              |
| ------ | ----------------- | ------------------------ |
| POST   | /users/sync       | Sync Firebase user       |
| POST   | /budget           | Create/update budget     |
| GET    | /budget/remaining | Get current budget stats |
| POST   | /expenses         | Add expense              |
| GET    | /expenses         | Get user expenses        |

---

## 🧪 Notes

* All endpoints require a valid Firebase token
* Budget is stored per month
* Expenses are categorized and typed (essential / optional)
* Frontend handles error display and validation

---

## 📌 Status

✅ Fully working full-stack app
🔧 Ready for UI improvements and analytics features

---

## 💡 Future Improvements

* Charts & visual analytics
* Better UI/UX feedback (toasts, loaders)
* Recurring expenses
* Deployment (Render / Vercel / Firebase Hosting)
