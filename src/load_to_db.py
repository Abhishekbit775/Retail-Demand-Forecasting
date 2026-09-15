import pandas as pd
import sqlite3
import os
import numpy as np

DB_PATH = "data/retail_demand.db"
SCHEMA_PATH = "sql/schema.sql"
CLEAN_PATH = "data/processed/retail_clean.csv"
WEEKLY_PATH = "data/processed/weekly_demand.csv"


def create_database():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()
    conn.executescript(schema)
    conn.commit()
    print(f"Database created: {DB_PATH}")
    return conn


def load_weekly_demand(conn):
    df = pd.read_csv(WEEKLY_PATH)
    df.to_sql("weekly_demand", conn, if_exists="replace", index=False)
    print(f"Loaded {len(df)} weekly demand rows")
    return df


def build_products_table(conn, weekly):
    products = weekly.groupby(["stockcode", "description", "abc_class"]).agg(
        total_revenue=("total_revenue", "sum"),
        total_quantity=("total_quantity", "sum"),
        avg_weekly_demand=("total_quantity", "mean"),
        demand_std=("total_quantity", "std"),
        weeks_of_data=("week", "count")
    ).reset_index()

    products["avg_weekly_demand"] = products["avg_weekly_demand"].round(2)
    products["demand_std"] = products["demand_std"].fillna(0).round(2)
    products["total_revenue"] = products["total_revenue"].round(2)

    products.to_sql("products", conn, if_exists="replace", index=False)
    print(f"Loaded {len(products)} products into products table")
    return products


def verify_database(conn):
    cursor = conn.cursor()

    print("\n--- Database Verification ---")

    cursor.execute("SELECT COUNT(*) FROM weekly_demand")
    print(f"Weekly demand rows: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM products")
    print(f"Total products: {cursor.fetchone()[0]}")

    print("\nTop 10 products by revenue:")
    cursor.execute("""
        SELECT stockcode, description, abc_class,
               ROUND(total_revenue, 2) as revenue,
               ROUND(avg_weekly_demand, 1) as avg_weekly
        FROM products
        ORDER BY total_revenue DESC
        LIMIT 10
    """)
    for row in cursor.fetchall():
        print(f"  [{row[2]}] {row[0]} | {row[1][:30]} | £{row[3]} | {row[4]}/week")

    print("\nABC summary:")
    cursor.execute("""
        SELECT abc_class,
               COUNT(*) as products,
               ROUND(SUM(total_revenue), 2) as revenue,
               ROUND(AVG(avg_weekly_demand), 1) as avg_weekly_demand
        FROM products
        GROUP BY abc_class
        ORDER BY abc_class
    """)
    for row in cursor.fetchall():
        print(f"  Class {row[0]}: {row[1]} products | £{row[2]} revenue | {row[3]} units/week avg")


def run_pipeline():
    print("=" * 60)
    print("Retail Demand Forecasting — Database Pipeline")
    print("=" * 60)

    conn = create_database()
    weekly = load_weekly_demand(conn)
    build_products_table(conn, weekly)
    verify_database(conn)

    conn.close()
    print("\nDatabase pipeline complete.")


if __name__ == "__main__":
    run_pipeline()