import sqlite3
import pandas as pd
from flask import Flask, render_template, jsonify, request
import os

app = Flask(__name__)
DATABASE = os.environ.get('DATABASE_PATH', 'student_expense_record.db')


def get_db():
    db_path = os.environ.get('DATABASE_PATH', 'student_expense_record.db')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute()
    conn.commit()
    conn.close()


def get_all_expenses():
    conn = get_db()
    rows = conn.execute('SELECT date, category, amount FROM expenses ORDER BY date').fetchall()
    conn.close()

    if not rows:
        return pd.DataFrame()

    data = [{'日期': r['date'], '类别': r['category'], '金额': r['amount']} for r in rows]
    return pd.DataFrame(data)


def get_statistics(start_date=None, end_date=None):
    df = get_all_expenses()

    if df.empty:
        return {
            'total_expense': 0,
            'daily_average': 0,
            'category_expense': {},
            'daily_trend': {},
            'date_range': {'min': None, 'max': None},
            'raw_table': []
        }

    if '金额' in df.columns:
        df['金额'] = pd.to_numeric(df['金额'], errors='coerce')
    if '日期' in df.columns:
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce').dt.strftime('%Y-%m-%d')

    df = df.dropna(subset=['日期', '金额'])

    if start_date:
        df = df[df['日期'] >= start_date]
    if end_date:
        df = df[df['日期'] <= end_date]

    if df.empty:
        return {
            'total_expense': 0,
            'daily_average': 0,
            'category_expense': {},
            'daily_trend': {},
            'date_range': {'min': None, 'max': None},
            'raw_table': []
        }

    total = round(df['金额'].sum(), 2)
    avg = round(df['金额'].mean(), 2)

    category_data = df.groupby('类别')['金额'].sum().round(2).to_dict()
    category_data = {str(k): round(float(v), 2) for k, v in category_data.items()}

    daily_data = df.groupby('日期')['金额'].sum().round(2).to_dict()
    daily_data = {str(k): round(float(v), 2) for k, v in daily_data.items()}

    dates = sorted(df['日期'].unique())
    date_min = dates[0] if dates else None
    date_max = dates[-1] if dates else None

    table_data = df.fillna('').to_dict(orient='records')
    for row in table_data:
        for key, val in row.items():
            if key == '金额' and val and val != 'nan':
                try:
                    row[key] = round(float(val), 2)
                except:
                    pass

    return {
        'total_expense': total,
        'daily_average': avg,
        'category_expense': category_data,
        'daily_trend': daily_data,
        'date_range': {'min': date_min, 'max': date_max},
        'raw_table': table_data
    }


def get_date_index():
    df = get_all_expenses()

    if df.empty or '日期' not in df.columns:
        return {
            'years': [],
            'months_by_year': {},
            'days_by_year_month': {},
            'date_range': {'min': None, 'max': None}
        }

    dates = pd.to_datetime(df['日期'], errors='coerce').dropna().dt.strftime('%Y-%m-%d')
    uniq = sorted(set(dates.tolist()))

    if not uniq:
        return {
            'years': [],
            'months_by_year': {},
            'days_by_year_month': {},
            'date_range': {'min': None, 'max': None}
        }

    years = sorted({int(d[0:4]) for d in uniq if len(d) >= 10})
    months_by_year = {str(y): [] for y in years}
    days_by_year_month = {}

    for ds in uniq:
        if len(ds) < 10:
            continue
        y, m, d = ds[0:4], ds[5:7], ds[8:10]
        if not (y.isdigit() and m.isdigit() and d.isdigit()):
            continue
        mi, di = int(m), int(d)
        if mi not in months_by_year[y]:
            months_by_year[y].append(mi)
        ym = f"{y}-{m}"
        if ym not in days_by_year_month:
            days_by_year_month[ym] = []
        if di not in days_by_year_month[ym]:
            days_by_year_month[ym].append(di)

    for y in months_by_year:
        months_by_year[y] = sorted(months_by_year[y])
    for ym in days_by_year_month:
        days_by_year_month[ym] = sorted(days_by_year_month[ym])

    return {
        'years': years,
        'months_by_year': months_by_year,
        'days_by_year_month': days_by_year_month,
        'date_range': {'min': uniq[0], 'max': uniq[-1]}
    }


@app.route('/')
def index():
    return render_template('frontend.html')


@app.route('/api/statistics')
def get_stats():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    stats = get_statistics(start_date=start_date, end_date=end_date)
    return jsonify({**stats, 'has_data': True})


@app.route('/api/date_index')
def get_dates():
    index = get_date_index()
    return jsonify({'has_data': True, 'date_index': index})


if __name__ == '__main__':
    init_db()
    print("数据库初始化完成")
    print("启动服务器...")
    app.run(debug=False, host='0.0.0.0', port=8000)
