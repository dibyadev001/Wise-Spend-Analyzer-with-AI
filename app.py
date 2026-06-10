"""
Wise Spend — Expense Tracker Backend
Flask + SQLite3 + OpenRouter AI
"""

import os
import json
import sqlite3
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template, send_from_directory
from functools import wraps

app = Flask(__name__, template_folder='templates', static_folder='static')

# ── Config ─────────────────────────────────────────────────────────────────────
DB_PATH         = os.path.join(os.path.dirname(__file__), 'wise_spend.db')
OPENROUTER_KEY  = os.environ.get('OPENROUTER_API_KEY', '')
OPENROUTER_URL  = 'https://openrouter.ai/api/v1/chat/completions'
AI_MODEL        = 'google/gemma-4-26b-a4b-it:free'

CATEGORIES = [
    'Food & Dining',
    'Transport',
    'Shopping',
    'Entertainment',
    'Health & Fitness',
    'Bills & Utilities',
    'Travel',
    'Education',
    'Groceries',
    'Other',
]

# ── Database ────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript('''
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            description TEXT    NOT NULL,
            note        TEXT    DEFAULT '',
            date        TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT    NOT NULL UNIQUE,
            amount      REAL    NOT NULL,
            period      TEXT    NOT NULL DEFAULT 'monthly',
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ai_insights (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt      TEXT    NOT NULL,
            response    TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    ''')

    conn.commit()
    conn.close()


# ── Helpers ─────────────────────────────────────────────────────────────────────
def row_to_dict(row):
    return dict(row) if row else None


def rows_to_list(rows):
    return [dict(r) for r in rows]


def current_month_range():
    now  = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        end = start.replace(year=now.year + 1, month=1)
    else:
        end = start.replace(month=now.month + 1)
    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')


# ── Routes ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html', categories=json.dumps(CATEGORIES))


# ─── Expenses ──────────────────────────────────────────────────────────────────

@app.route('/api/expenses', methods=['GET'])
def get_expenses():
    conn = get_db()
    try:
        category = request.args.get('category', '')
        start    = request.args.get('start', '')
        end      = request.args.get('end', '')
        search   = request.args.get('search', '')
        limit    = int(request.args.get('limit', 50))
        offset   = int(request.args.get('offset', 0))

        query  = 'SELECT * FROM expenses WHERE 1=1'
        params = []

        if category:
            query += ' AND category = ?'
            params.append(category)
        if start:
            query += ' AND date >= ?'
            params.append(start)
        if end:
            query += ' AND date <= ?'
            params.append(end)
        if search:
            query += ' AND (description LIKE ? OR note LIKE ?)'
            params += [f'%{search}%', f'%{search}%']

        query += ' ORDER BY date DESC, id DESC LIMIT ? OFFSET ?'
        params += [limit, offset]

        expenses = rows_to_list(conn.execute(query, params).fetchall())

        # Total count
        count_q  = query.replace('SELECT *', 'SELECT COUNT(*)')
        count_q  = count_q[:count_q.rfind('LIMIT')]
        total    = conn.execute(count_q, params[:-2]).fetchone()[0]

        return jsonify({'expenses': expenses, 'total': total})
    finally:
        conn.close()


@app.route('/api/expenses', methods=['POST'])
def add_expense():
    data = request.get_json()
    conn = get_db()
    try:
        amount      = float(data['amount'])
        category    = data['category']
        description = data.get('description', '').strip()
        note        = data.get('note', '').strip()
        date        = data.get('date', datetime.now().strftime('%Y-%m-%d'))

        if amount <= 0:
            return jsonify({'error': 'Amount must be positive'}), 400
        if not description:
            return jsonify({'error': 'Description is required'}), 400
        if category not in CATEGORIES:
            return jsonify({'error': 'Invalid category'}), 400

        cur = conn.execute(
            'INSERT INTO expenses (amount, category, description, note, date) VALUES (?, ?, ?, ?, ?)',
            (amount, category, description, note, date)
        )
        conn.commit()

        expense = row_to_dict(conn.execute('SELECT * FROM expenses WHERE id = ?', (cur.lastrowid,)).fetchone())
        return jsonify({'expense': expense}), 201
    finally:
        conn.close()


@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
def update_expense(expense_id):
    data = request.get_json()
    conn = get_db()
    try:
        exp = conn.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,)).fetchone()
        if not exp:
            return jsonify({'error': 'Not found'}), 404

        amount      = float(data.get('amount',      exp['amount']))
        category    = data.get('category',    exp['category'])
        description = data.get('description', exp['description'])
        note        = data.get('note',        exp['note'])
        date        = data.get('date',        exp['date'])

        conn.execute(
            'UPDATE expenses SET amount=?, category=?, description=?, note=?, date=? WHERE id=?',
            (amount, category, description, note, date, expense_id)
        )
        conn.commit()
        expense = row_to_dict(conn.execute('SELECT * FROM expenses WHERE id = ?', (expense_id,)).fetchone())
        return jsonify({'expense': expense})
    finally:
        conn.close()


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        conn.commit()
        return jsonify({'deleted': expense_id})
    finally:
        conn.close()


# ─── Statistics ─────────────────────────────────────────────────────────────────

@app.route('/api/stats/summary')
def stats_summary():
    conn = get_db()
    try:
        month_start, month_end = current_month_range()

        # This month total
        month_total = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date >= ? AND date < ?',
            (month_start, month_end)
        ).fetchone()[0]

        # Last month
        prev_start = (datetime.strptime(month_start, '%Y-%m-%d') - timedelta(days=1)).replace(day=1).strftime('%Y-%m-%d')
        prev_total = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date >= ? AND date < ?',
            (prev_start, month_start)
        ).fetchone()[0]

        # Category breakdown this month
        cats = rows_to_list(conn.execute(
            '''SELECT category, COALESCE(SUM(amount), 0) as total, COUNT(*) as count
               FROM expenses WHERE date >= ? AND date < ?
               GROUP BY category ORDER BY total DESC''',
            (month_start, month_end)
        ).fetchall())

        # Daily spending this month (last 30 days)
        daily = rows_to_list(conn.execute(
            '''SELECT date, COALESCE(SUM(amount), 0) as total
               FROM expenses WHERE date >= ? AND date < ?
               GROUP BY date ORDER BY date ASC''',
            (month_start, month_end)
        ).fetchall())

        # Total all time
        all_time = conn.execute('SELECT COALESCE(SUM(amount), 0) FROM expenses').fetchone()[0]
        tx_count = conn.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]

        return jsonify({
            'month_total':  round(month_total, 2),
            'prev_total':   round(prev_total, 2),
            'all_time':     round(all_time, 2),
            'tx_count':     tx_count,
            'categories':   cats,
            'daily':        daily,
            'month_start':  month_start,
        })
    finally:
        conn.close()


# ─── Budgets ────────────────────────────────────────────────────────────────────

@app.route('/api/budgets', methods=['GET'])
def get_budgets():
    conn = get_db()
    try:
        month_start, month_end = current_month_range()
        budgets = rows_to_list(conn.execute('SELECT * FROM budgets ORDER BY category').fetchall())

        # Add spent amount for this month
        for b in budgets:
            spent = conn.execute(
                'SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE category=? AND date>=? AND date<?',
                (b['category'], month_start, month_end)
            ).fetchone()[0]
            b['spent']   = round(spent, 2)
            b['percent'] = round((spent / b['amount']) * 100, 1) if b['amount'] > 0 else 0

        return jsonify({'budgets': budgets})
    finally:
        conn.close()


@app.route('/api/budgets', methods=['POST'])
def set_budget():
    data = request.get_json()
    conn = get_db()
    try:
        category = data['category']
        amount   = float(data['amount'])
        period   = data.get('period', 'monthly')

        if category not in CATEGORIES:
            return jsonify({'error': 'Invalid category'}), 400

        conn.execute(
            '''INSERT INTO budgets (category, amount, period, updated_at)
               VALUES (?, ?, ?, datetime('now'))
               ON CONFLICT(category) DO UPDATE SET amount=excluded.amount,
               period=excluded.period, updated_at=excluded.updated_at''',
            (category, amount, period)
        )
        conn.commit()
        budget = row_to_dict(conn.execute('SELECT * FROM budgets WHERE category=?', (category,)).fetchone())
        return jsonify({'budget': budget}), 201
    finally:
        conn.close()


@app.route('/api/budgets/<int:budget_id>', methods=['DELETE'])
def delete_budget(budget_id):
    conn = get_db()
    try:
        conn.execute('DELETE FROM budgets WHERE id = ?', (budget_id,))
        conn.commit()
        return jsonify({'deleted': budget_id})
    finally:
        conn.close()


# ─── OpenRouter AI ──────────────────────────────────────────────────────────────

@app.route('/api/ai/insights', methods=['POST'])
def ai_insights():
    data = request.get_json()
    user_prompt = data.get('prompt', '').strip()
    # Accept API key from frontend (stored in localStorage) OR fall back to env var
    client_key  = data.get('api_key', '').strip()
    effective_key = client_key if client_key else OPENROUTER_KEY

    if not user_prompt:
        return jsonify({'error': 'Prompt is required'}), 400

    conn = get_db()
    try:
        # Build spending context for AI
        month_start, month_end = current_month_range()
        cats = rows_to_list(conn.execute(
            '''SELECT category, COALESCE(SUM(amount), 0) as total
               FROM expenses WHERE date >= ? AND date < ?
               GROUP BY category ORDER BY total DESC''',
            (month_start, month_end)
        ).fetchall())

        recent = rows_to_list(conn.execute(
            'SELECT amount, category, description, date FROM expenses ORDER BY date DESC LIMIT 15'
        ).fetchall())

        month_total = conn.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date >= ? AND date < ?',
            (month_start, month_end)
        ).fetchone()[0]

        context = f"""You are WiseAI, a friendly personal finance advisor inside a spending tracker app.

Current month spending: \u20b9{round(month_total, 2)}

Category breakdown this month:
{chr(10).join([f"- {c['category']}: \u20b9{round(c['total'], 2)}" for c in cats]) or "No data yet"}

Recent transactions (up to 15):
{chr(10).join([f"- {e['date']} | {e['category']} | \u20b9{e['amount']} | {e['description']}" for e in recent]) or "No transactions yet"}

Provide concise, actionable advice. Use bullet points. Be warm and encouraging. Keep response under 200 words."""

        # Check key
        if not effective_key or effective_key == 'YOUR_OPENROUTER_API_KEY_HERE':
            return jsonify({'error': '🔑 No API key found. Enter your OpenRouter key in the AI tab (free at openrouter.ai).'}), 400

        resp = requests.post(
            OPENROUTER_URL,
            headers={
                'Authorization': f'Bearer {effective_key}',
                'Content-Type':  'application/json',
                'HTTP-Referer':  'http://localhost:5000',
                'X-Title':       'WiseSpend Tracker',
            },
            json={
                'model': AI_MODEL,
                # Gemma (Google AI Studio) does not support 'system' role.
                # Merge context into the user message instead.
                'messages': [
                    {'role': 'user', 'content': f"{context}\n\nUser question: {user_prompt}"},
                ],
                'max_tokens': 400,
            },
            timeout=30
        )

        if resp.status_code != 200:
            err = resp.json().get('error', {}).get('message', resp.text)
            return jsonify({'error': f'OpenRouter error: {err}'}), 502

        ai_text = resp.json()['choices'][0]['message']['content'].strip()

        # Cache insight
        conn.execute('INSERT INTO ai_insights (prompt, response) VALUES (?, ?)', (user_prompt, ai_text))
        conn.commit()

        return jsonify({'response': ai_text})
    finally:
        conn.close()


@app.route('/api/ai/history')
def ai_history():
    conn = get_db()
    try:
        rows = rows_to_list(conn.execute(
            'SELECT * FROM ai_insights ORDER BY created_at DESC LIMIT 10'
        ).fetchall())
        return jsonify({'history': rows})
    finally:
        conn.close()


# ─── Categories ─────────────────────────────────────────────────────────────────

@app.route('/api/categories')
def get_categories():
    return jsonify({'categories': CATEGORIES})


# ─── Seed demo data ──────────────────────────────────────────────────────────────

@app.route('/api/seed', methods=['POST'])
def seed_data():
    """Insert realistic demo expenses for the current month."""
    conn = get_db()
    try:
        existing = conn.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]
        if existing > 0:
            return jsonify({'message': 'Data already exists, skipping seed.'})

        now   = datetime.now()
        year  = now.year
        month = now.month

        def d(day): return f'{year}-{month:02d}-{min(day, now.day):02d}'

        samples = [
            (850,  'Food & Dining',     'Team lunch at cafe',       '',                d(2)),
            (320,  'Transport',         'Uber to office',           'Morning commute',  d(3)),
            (2400, 'Shopping',          'New headphones',           'Sony WH-1000XM5',  d(4)),
            (180,  'Food & Dining',     'Coffee & snacks',          '',                d(5)),
            (1200, 'Groceries',         'Weekly grocery run',       'Big Basket order', d(6)),
            (499,  'Entertainment',     'Netflix subscription',     'Monthly',          d(7)),
            (650,  'Food & Dining',     'Dinner with friends',      'Barbeque Nation',  d(8)),
            (350,  'Transport',         'Auto rickshaw rides',      '',                d(9)),
            (2000, 'Bills & Utilities', 'Electricity bill',         'June 2026',        d(10)),
            (800,  'Health & Fitness',  'Gym membership',           'Monthly fee',      d(11)),
            (450,  'Food & Dining',     'Zomato order',             'Dinner',           d(12)),
            (1500, 'Education',         'Udemy course',             'Python Advanced',  d(13)),
            (280,  'Transport',         'Petrol',                   '',                d(14)),
            (900,  'Groceries',         'Vegetables & fruits',      'Local market',     d(15)),
            (1800, 'Shopping',          'Clothes',                  'Myntra sale',      d(16)),
            (300,  'Food & Dining',     'Breakfast',                '',                d(17)),
            (599,  'Entertainment',     'Spotify premium',          '3-month plan',     d(18)),
            (750,  'Health & Fitness',  'Doctor consultation',      'General checkup',  d(19)),
            (400,  'Transport',         'Ola cab',                  'Airport drop',     d(20)),
            (1100, 'Food & Dining',     'Birthday dinner',          'Restaurant bill',  d(min(21, now.day))),
        ]

        for amount, cat, desc, note, date in samples:
            conn.execute(
                'INSERT INTO expenses (amount, category, description, note, date) VALUES (?, ?, ?, ?, ?)',
                (amount, cat, desc, note, date)
            )

        # Add some budgets too
        budgets = [
            ('Food & Dining',    3000, 'monthly'),
            ('Transport',        1500, 'monthly'),
            ('Shopping',         3000, 'monthly'),
            ('Groceries',        2500, 'monthly'),
            ('Entertainment',    1000, 'monthly'),
            ('Bills & Utilities',2500, 'monthly'),
        ]
        for cat, amt, period in budgets:
            conn.execute(
                '''INSERT OR IGNORE INTO budgets (category, amount, period) VALUES (?, ?, ?)''',
                (cat, amt, period)
            )

        conn.commit()
        return jsonify({'message': f'Seeded {len(samples)} expenses and {len(budgets)} budgets.'})
    finally:
        conn.close()


# ─── Bootstrap ─────────────────────────────────────────────────────────────────

# Always initialise DB (works with both `flask run` and `python app.py`)
with app.app_context():
    init_db()

if __name__ == '__main__':
    print('WiseSpend running at http://localhost:5000')
    app.run(debug=True, port=5000)
