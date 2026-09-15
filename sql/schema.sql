CREATE TABLE IF NOT EXISTS products (
    stockcode TEXT PRIMARY KEY,
    description TEXT,
    abc_class TEXT,
    total_revenue REAL,
    total_quantity INTEGER,
    avg_weekly_demand REAL,
    demand_std REAL,
    weeks_of_data INTEGER
);

CREATE TABLE IF NOT EXISTS weekly_demand (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stockcode TEXT,
    description TEXT,
    year INTEGER,
    week INTEGER,
    abc_class TEXT,
    total_quantity INTEGER,
    total_revenue REAL,
    transaction_count INTEGER
);

CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stockcode TEXT,
    description TEXT,
    abc_class TEXT,
    forecast_week INTEGER,
    forecast_year INTEGER,
    ma_forecast REAL,
    exp_forecast REAL,
    reg_forecast REAL,
    best_method TEXT,
    best_forecast REAL,
    mape REAL,
    rmse REAL,
    mae REAL
);

CREATE TABLE IF NOT EXISTS stockout_risk (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stockcode TEXT,
    description TEXT,
    abc_class TEXT,
    avg_weekly_demand REAL,
    demand_std REAL,
    forecast_next_week REAL,
    current_inventory_proxy REAL,
    lead_time_days INTEGER,
    safety_stock REAL,
    reorder_point REAL,
    recommended_order_qty REAL,
    stockout_risk_score REAL,
    risk_level TEXT
);

CREATE TABLE IF NOT EXISTS model_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stockcode TEXT,
    method TEXT,
    mape REAL,
    rmse REAL,
    mae REAL,
    is_best INTEGER DEFAULT 0
);