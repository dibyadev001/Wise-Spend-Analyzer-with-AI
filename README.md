# 💸 WiseSpend — Smart Expense Tracker with AI Insights

> A full-stack personal finance tracker powered by **Flask + SQLite3 + Tailwind CSS** and **Google Gemma 4 AI** (via OpenRouter) — completely free to run.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=flat-square&logo=flask)
![SQLite](https://img.shields.io/badge/SQLite-3-blue?style=flat-square&logo=sqlite)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-CDN-38BDF8?style=flat-square&logo=tailwindcss)
![AI](https://img.shields.io/badge/AI-Gemma%204%20Free-orange?style=flat-square&logo=google)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## ✨ Features

### 📊 Dashboard
- **4 Stat Cards** — This Month total, All Time, Average per Day, Top Category
- **Daily Spending Line Chart** (Chart.js) — visualises spending day-by-day for the current month
- **Category Donut Chart** — instant breakdown of where money is going
- **Recent Transactions** — last 5 expenses at a glance

### 📋 Transactions
- Full transaction history with **search**, **category filter**, and **date range** filter
- **Add / Edit / Delete** expenses via animated modals
- Paginated view (20 per page)
- Supports amount, category (10 types), description, date, and optional notes

### 🎯 Budgets
- Set **monthly limits** per category
- Color-coded **animated progress bars**
  - 🟢 Green — within budget
  - 🟡 Amber — above 80%
  - 🔴 Red — over budget
- Live "₹X left" / "Over by ₹Y" calculations

### ✨ WiseAI — Gemma 4 Powered Insights
- **Chat interface** that reads your actual spending data in real-time
- Asks meaningful financial questions with **Quick Prompt buttons**
- Powered by `google/gemma-4-26b-a4b-it:free` via OpenRouter (100% free)
- Paste your API key directly in the UI — no `.env` setup required
- AI responses cached in SQLite for history

---

## 🖥️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python + Flask 3 |
| Database | SQLite3 (zero config, file-based) |
| Frontend | HTML + Tailwind CSS (CDN) + Vanilla JS |
| Charts | Chart.js 4 |
| Icons | Lucide Icons |
| AI | Google Gemma 4 26B via OpenRouter API (free tier) |

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/your-username/wisespend.git
cd wisespend/wise-spend
```

### 2. Install dependencies
```bash
pip install flask requests
```

### 3. Run the server
```bash
python app.py
```

Open **http://localhost:5000** in your browser.

### 4. Seed demo data (optional)
```bash
curl -X POST http://localhost:5000/api/seed
```
This loads 20 realistic sample expenses and 6 category budgets so the dashboard looks great immediately.

### 5. Enable AI Insights (free)
1. Sign up at **[openrouter.ai](https://openrouter.ai)** (free)
2. Generate a free API key
3. In the app, go to **AI Insights → AI Config**
4. Paste your key and click **Save Key**
5. Start chatting with WiseAI!

---

## 📁 Project Structure

```
wise-spend/
├── app.py                  # Flask backend + all API routes
├── requirements.txt        # flask, requests
├── wise_spend.db           # SQLite database (auto-created)
└── templates/
    └── index.html          # Single-page frontend (Tailwind + Chart.js)
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Main app |
| GET | `/api/expenses` | List expenses (with filters) |
| POST | `/api/expenses` | Add expense |
| PUT | `/api/expenses/<id>` | Update expense |
| DELETE | `/api/expenses/<id>` | Delete expense |
| GET | `/api/stats/summary` | Dashboard stats + chart data |
| GET | `/api/budgets` | List budgets with spent amounts |
| POST | `/api/budgets` | Set/update a budget |
| DELETE | `/api/budgets/<id>` | Remove a budget |
| POST | `/api/ai/insights` | Ask WiseAI a question |
| GET | `/api/ai/history` | Last 10 AI conversations |
| POST | `/api/seed` | Load demo data |

---

## 🏷️ Expense Categories

🍽️ Food & Dining · 🚗 Transport · 🛍️ Shopping · 🎬 Entertainment · 💪 Health & Fitness · ⚡ Bills & Utilities · ✈️ Travel · 📚 Education · 🛒 Groceries · 📦 Other

---

## 🤖 AI Model

WiseSpend uses **Google Gemma 4 26B** (`google/gemma-4-26b-a4b-it:free`) via the OpenRouter API.

- **Cost:** $0.00 — completely free tier
- **Provider:** Google AI Studio
- **Context:** The AI automatically receives your current month's spending breakdown and recent transactions before answering

> **Note for developers:** Gemma 4 via Google AI Studio does not support the OpenAI-style `system` role. The app merges the financial context directly into the user message to maintain compatibility.

---

## 📸 Screenshots

| Dashboard | AI Insights | Budgets |
|-----------|-------------|---------|
| Stat cards + charts | Gemma-powered chat | Progress bars |

---

## 🙏 Acknowledgements

- [OpenRouter](https://openrouter.ai) — free AI model routing
- [Google Gemma 4](https://blog.google/technology/developers/google-gemma-4/) — open AI model
- [Chart.js](https://www.chartjs.org/) — beautiful charts
- [Lucide Icons](https://lucide.dev/) — clean icon set
- [Tailwind CSS](https://tailwindcss.com/) — utility-first CSS

---

## 📄 License

MIT License — free to use, modify and distribute.
