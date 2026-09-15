import pandas as pd
import numpy as np
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns
import os

DB_PATH = "data/retail_demand.db"
PLOTS_PATH = "dashboard/"

LEAD_TIME_DAYS = {
    "A": 3,
    "B": 5,
    "C": 7
}

SERVICE_LEVEL_Z = {
    "A": 1.65,
    "B": 1.28,
    "C": 1.04
}


def load_data():
    conn = sqlite3.connect(DB_PATH)
    forecasts = pd.read_sql("SELECT * FROM forecasts", conn)
    products = pd.read_sql("SELECT * FROM products", conn)
    conn.close()
    return forecasts, products


def compute_safety_stock(avg_demand, demand_std, lead_time_days, abc_class):
    z = SERVICE_LEVEL_Z.get(abc_class, 1.28)
    daily_demand = avg_demand / 7
    daily_std = demand_std / 7
    safety_stock = z * daily_std * np.sqrt(lead_time_days)
    return max(0, round(safety_stock, 2))


def compute_reorder_point(avg_demand, demand_std, lead_time_days, abc_class):
    daily_demand = avg_demand / 7
    safety_stock = compute_safety_stock(avg_demand, demand_std, lead_time_days, abc_class)
    reorder_point = (daily_demand * lead_time_days) + safety_stock
    return round(reorder_point, 2)


def compute_recommended_order(forecast, avg_demand, demand_std, lead_time_days, abc_class):
    safety_stock = compute_safety_stock(avg_demand, demand_std, lead_time_days, abc_class)
    current_inventory_proxy = avg_demand * 1.5
    order_qty = (forecast * (lead_time_days / 7)) + safety_stock - current_inventory_proxy
    order_qty = max(0, order_qty)
    return round(order_qty, 2), round(current_inventory_proxy, 2), round(safety_stock, 2)


def compute_stockout_risk_score(forecast, avg_demand, demand_std, current_inventory_proxy):
    if avg_demand == 0:
        return 0
    days_of_stock = current_inventory_proxy / (avg_demand / 7) if avg_demand > 0 else 999
    demand_volatility = demand_std / avg_demand if avg_demand > 0 else 0
    forecast_vs_avg = forecast / avg_demand if avg_demand > 0 else 1

    risk_score = (
        (max(0, 7 - days_of_stock) / 7 * 40) +
        (min(demand_volatility, 1) * 30) +
        (min(max(forecast_vs_avg - 1, 0), 1) * 30)
    )
    return round(min(risk_score, 100), 2)


def classify_risk(score):
    if score >= 60:
        return "HIGH"
    elif score >= 30:
        return "MEDIUM"
    else:
        return "LOW"


def build_recommendations(forecasts, products):
    merged = forecasts.merge(
        products[["stockcode", "avg_weekly_demand", "demand_std"]],
        on="stockcode",
        how="left"
    )

    recommendations = []

    for _, row in merged.iterrows():
        abc = row["abc_class"]
        lead_time = LEAD_TIME_DAYS.get(abc, 5)
        avg_demand = row["avg_weekly_demand"]
        demand_std = row["demand_std"]
        forecast = row["best_forecast"]

        order_qty, inventory_proxy, safety_stock = compute_recommended_order(
            forecast, avg_demand, demand_std, lead_time, abc
        )

        reorder_point = compute_reorder_point(avg_demand, demand_std, lead_time, abc)

        risk_score = compute_stockout_risk_score(
            forecast, avg_demand, demand_std, inventory_proxy
        )

        recommendations.append({
            "stockcode": row["stockcode"],
            "description": row["description"],
            "abc_class": abc,
            "avg_weekly_demand": round(avg_demand, 2),
            "demand_std": round(demand_std, 2),
            "forecast_next_week": forecast,
            "current_inventory_proxy": inventory_proxy,
            "lead_time_days": lead_time,
            "safety_stock": safety_stock,
            "reorder_point": reorder_point,
            "recommended_order_qty": order_qty,
            "stockout_risk_score": risk_score,
            "risk_level": classify_risk(risk_score)
        })

    return pd.DataFrame(recommendations)


def save_recommendations(recommendations, conn):
    recommendations.to_sql("stockout_risk", conn, if_exists="replace", index=False)
    print(f"Saved {len(recommendations)} procurement recommendations")


def print_summary(recommendations):
    print("\n--- Procurement Summary ---")

    print("\nRisk level distribution:")
    print(recommendations["risk_level"].value_counts().to_string())

    print("\nHigh risk products by ABC class:")
    high_risk = recommendations[recommendations["risk_level"] == "HIGH"]
    print(high_risk["abc_class"].value_counts().to_string())

    print("\nTop 10 HIGH RISK A-class products to order NOW:")
    urgent = recommendations[
        (recommendations["risk_level"] == "HIGH") &
        (recommendations["abc_class"] == "A")
    ].nlargest(10, "stockout_risk_score")

    for _, row in urgent.iterrows():
        print(f"  {row['stockcode']} | {row['description'][:28]} | "
              f"Risk: {row['stockout_risk_score']} | "
              f"Order: {row['recommended_order_qty']:.0f} units | "
              f"Safety Stock: {row['safety_stock']:.0f}")

    print("\nAverage recommended order by ABC class:")
    print(recommendations.groupby("abc_class")["recommended_order_qty"].mean().round(1).to_string())


def generate_plots(recommendations):
    os.makedirs(PLOTS_PATH, exist_ok=True)

    plt.figure(figsize=(8, 5))
    risk_counts = recommendations["risk_level"].value_counts()
    colors = {"HIGH": "#E24B4A", "MEDIUM": "#EF9F27", "LOW": "#1D9E75"}
    plt.bar(risk_counts.index, risk_counts.values,
            color=[colors.get(x, "grey") for x in risk_counts.index])
    plt.title("Stockout Risk Distribution across Products")
    plt.xlabel("Risk Level")
    plt.ylabel("Number of Products")
    for i, (idx, val) in enumerate(risk_counts.items()):
        plt.text(i, val + 5, str(val), ha="center", fontweight="bold")
    plt.tight_layout()
    plt.savefig(f"{PLOTS_PATH}stockout_risk_distribution.png", dpi=150)
    plt.close()
    print("Saved: stockout_risk_distribution.png")

    plt.figure(figsize=(9, 5))
    abc_risk = recommendations.groupby(["abc_class", "risk_level"]).size().unstack(fill_value=0)
    abc_risk.plot(kind="bar", color=["#1D9E75", "#EF9F27", "#E24B4A"],
                  figsize=(9, 5))
    plt.title("Risk Level Distribution by ABC Class")
    plt.xlabel("ABC Class")
    plt.ylabel("Number of Products")
    plt.xticks(rotation=0)
    plt.legend(title="Risk Level")
    plt.tight_layout()
    plt.savefig(f"{PLOTS_PATH}risk_by_abc_class.png", dpi=150)
    plt.close()
    print("Saved: risk_by_abc_class.png")

    plt.figure(figsize=(9, 5))
    sample = recommendations.sample(min(1000, len(recommendations)), random_state=42)
    colors_map = {"HIGH": "#E24B4A", "MEDIUM": "#EF9F27", "LOW": "#1D9E75"}
    for risk_level, group in sample.groupby("risk_level"):
        plt.scatter(group["avg_weekly_demand"], group["forecast_next_week"],
                   label=risk_level, alpha=0.5,
                   color=colors_map.get(risk_level, "grey"))
    plt.title("Average Weekly Demand vs Forecast (colored by risk)")
    plt.xlabel("Average Weekly Demand (units)")
    plt.ylabel("Forecast Next Week (units)")
    plt.legend(title="Risk Level")
    plt.tight_layout()
    plt.savefig(f"{PLOTS_PATH}demand_vs_forecast.png", dpi=150)
    plt.close()
    print("Saved: demand_vs_forecast.png")

    plt.figure(figsize=(9, 5))
    top_products = recommendations[recommendations["abc_class"] == "A"].nlargest(15, "avg_weekly_demand")
    plt.barh(
        [d[:25] for d in top_products["description"]],
        top_products["recommended_order_qty"],
        color="#378ADD"
    )
    plt.title("Top 15 A-Class Products — Recommended Order Quantity")
    plt.xlabel("Units to Order")
    plt.tight_layout()
    plt.savefig(f"{PLOTS_PATH}top_products_order_qty.png", dpi=150)
    plt.close()
    print("Saved: top_products_order_qty.png")


def run_recommendations():
    print("=" * 60)
    print("Retail Demand Forecasting — Procurement Recommendations")
    print("=" * 60)

    forecasts, products = load_data()
    recommendations = build_recommendations(forecasts, products)

    conn = sqlite3.connect(DB_PATH)
    save_recommendations(recommendations, conn)
    conn.close()

    print_summary(recommendations)
    generate_plots(recommendations)

    print("\nRecommendation engine complete.")
    return recommendations


if __name__ == "__main__":
    recommendations = run_recommendations()