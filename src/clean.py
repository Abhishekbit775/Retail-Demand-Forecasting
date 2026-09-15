import pandas as pd
import numpy as np
import os

RAW_PATH = "data/raw/online_retail.xlsx"
PROCESSED_PATH = "data/processed/retail_clean.csv"


def load_data():
    print("Loading Excel file — this takes 30-60 seconds...")
    df = pd.read_excel(RAW_PATH)
    print(f"Loaded {len(df)} rows")
    return df


def remove_cancellations(df):
    initial = len(df)
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]
    print(f"Removed {initial - len(df)} cancellation rows")
    return df


def remove_bad_rows(df):
    initial = len(df)

    df = df[df["Quantity"] > 0]
    df = df[df["UnitPrice"] > 0]
    df = df.dropna(subset=["Description"])

    non_product_codes = ["POST", "DOT", "M", "BANK CHARGES", "PADS", "D", "C2"]
    df = df[~df["StockCode"].astype(str).str.upper().isin(non_product_codes)]
    df = df[~df["StockCode"].astype(str).str.startswith("AMAZON")]

    print(f"Removed {initial - len(df)} bad rows")
    return df


def clean_columns(df):
    df.columns = [col.strip().lower() for col in df.columns]

    df["description"] = df["description"].astype(str).str.strip().str.upper()
    df["country"] = df["country"].astype(str).str.strip()
    df["stockcode"] = df["stockcode"].astype(str).str.strip().str.upper()

    df["invoicedate"] = pd.to_datetime(df["invoicedate"])
    df["date"] = df["invoicedate"].dt.date
    df["year"] = df["invoicedate"].dt.year
    df["month"] = df["invoicedate"].dt.month
    df["month_name"] = df["invoicedate"].dt.strftime("%B")
    df["week"] = df["invoicedate"].dt.isocalendar().week.astype(int)
    df["day_of_week"] = df["invoicedate"].dt.day_name()
    df["is_weekend"] = df["invoicedate"].dt.dayofweek >= 5
    df["quarter"] = df["invoicedate"].dt.quarter

    df["revenue"] = (df["quantity"] * df["unitprice"]).round(2)

    return df


def add_abc_classification(df):
    product_revenue = df.groupby("stockcode")["revenue"].sum().reset_index()
    product_revenue = product_revenue.sort_values("revenue", ascending=False)

    total_revenue = product_revenue["revenue"].sum()
    product_revenue["cumulative_pct"] = (
        product_revenue["revenue"].cumsum() / total_revenue * 100
    )

    def classify(pct):
        if pct <= 80:
            return "A"
        elif pct <= 95:
            return "B"
        else:
            return "C"

    product_revenue["abc_class"] = product_revenue["cumulative_pct"].apply(classify)

    df = df.merge(
        product_revenue[["stockcode", "abc_class"]],
        on="stockcode",
        how="left"
    )

    print("\nABC Classification:")
    print(df.groupby("abc_class")["stockcode"].nunique().rename("unique_products"))
    print(df.groupby("abc_class")["revenue"].sum().round(2).rename("total_revenue"))

    return df


def build_weekly_demand(df):
    weekly = df.groupby(["stockcode", "description", "year", "week", "abc_class"]).agg(
        total_quantity=("quantity", "sum"),
        total_revenue=("revenue", "sum"),
        transaction_count=("invoiceno", "nunique")
    ).reset_index()

    weekly = weekly.sort_values(["stockcode", "year", "week"])

    print(f"\nWeekly demand table: {len(weekly)} rows")
    print(f"Unique products in weekly table: {weekly['stockcode'].nunique()}")

    return weekly


def save_data(df, weekly):
    os.makedirs("data/processed", exist_ok=True)

    df.to_csv(PROCESSED_PATH, index=False)
    print(f"\nClean transactions saved: {PROCESSED_PATH}")
    print(f"Shape: {df.shape}")

    weekly_path = "data/processed/weekly_demand.csv"
    weekly.to_csv(weekly_path, index=False)
    print(f"Weekly demand saved: {weekly_path}")
    print(f"Shape: {weekly.shape}")


def run_cleaning_pipeline():
    print("=" * 60)
    print("Retail Demand Forecasting — Cleaning Pipeline")
    print("=" * 60)

    df = load_data()
    df = remove_cancellations(df)
    df = remove_bad_rows(df)
    df = clean_columns(df)
    df = add_abc_classification(df)
    weekly = build_weekly_demand(df)
    save_data(df, weekly)

    print("\nCleaning pipeline complete.")
    return df, weekly


if __name__ == "__main__":
    df, weekly = run_cleaning_pipeline()