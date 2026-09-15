import pandas as pd
import numpy as np
import sqlite3
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
import warnings
warnings.filterwarnings("ignore")

DB_PATH = "data/retail_demand.db"
MIN_WEEKS = 8


def load_data():
    conn = sqlite3.connect(DB_PATH)
    weekly = pd.read_sql("SELECT * FROM weekly_demand", conn)
    products = pd.read_sql("SELECT * FROM products WHERE weeks_of_data >= 8", conn)
    conn.close()
    return weekly, products


def compute_mape(actual, predicted):
    actual = np.array(actual)
    predicted = np.array(predicted)
    mask = actual != 0
    if mask.sum() == 0:
        return 999
    return round(np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100, 2)


def compute_rmse(actual, predicted):
    return round(np.sqrt(mean_squared_error(actual, predicted)), 2)


def compute_mae(actual, predicted):
    return round(mean_absolute_error(actual, predicted), 2)


def moving_average_forecast(series, window=4):
    if len(series) < window:
        return series.mean(), series.mean()
    train = series[:-4]
    test = series[-4:]
    predictions = []
    history = list(train)
    for _ in range(len(test)):
        pred = np.mean(history[-window:])
        predictions.append(pred)
        history.append(pred)
    next_forecast = np.mean(list(series)[-window:])
    return predictions, next_forecast


def exponential_smoothing_forecast(series):
    if len(series) < 8:
        return [series.mean()] * 4, series.mean()
    train = series[:-4]
    test = series[-4:]
    try:
        model = SimpleExpSmoothing(train.values).fit(optimized=True)
        predictions = model.forecast(len(test)).tolist()
        next_forecast = model.forecast(1)[0]
        return predictions, next_forecast
    except:
        return moving_average_forecast(series)


def regression_forecast(series, week_numbers):
    if len(series) < 8:
        return [series.mean()] * 4, series.mean()

    train_x = week_numbers[:-4].values.reshape(-1, 1)
    train_y = series[:-4].values
    test_x = week_numbers[-4:].values.reshape(-1, 1)

    model = LinearRegression()
    model.fit(train_x, train_y)

    predictions = model.predict(test_x).tolist()
    next_week = week_numbers.max() + 1
    next_forecast = model.predict([[next_week]])[0]
    next_forecast = max(0, next_forecast)

    return predictions, next_forecast


def forecast_product(stockcode, weekly_df):
    product_data = weekly_df[weekly_df["stockcode"] == stockcode].copy()
    product_data = product_data.sort_values(["year", "week"])

    if len(product_data) < MIN_WEEKS:
        return None

    series = product_data["total_quantity"].reset_index(drop=True)
    week_numbers = pd.Series(range(len(series)))
    test_actual = series[-4:].values

    ma_preds, ma_next = moving_average_forecast(series)
    exp_preds, exp_next = exponential_smoothing_forecast(series)
    reg_preds, reg_next = regression_forecast(series, week_numbers)

    ma_mape = compute_mape(test_actual, ma_preds)
    exp_mape = compute_mape(test_actual, exp_preds)
    reg_mape = compute_mape(test_actual, reg_preds)

    ma_rmse = compute_rmse(test_actual, ma_preds)
    exp_rmse = compute_rmse(test_actual, exp_preds)
    reg_rmse = compute_rmse(test_actual, reg_preds)

    ma_mae = compute_mae(test_actual, ma_preds)
    exp_mae = compute_mae(test_actual, exp_preds)
    reg_mae = compute_mae(test_actual, reg_preds)

    methods = {
        "moving_average": (ma_mape, ma_rmse, ma_mae, ma_next),
        "exp_smoothing": (exp_mape, exp_rmse, exp_mae, exp_next),
        "regression": (reg_mape, reg_rmse, reg_mae, reg_next),
    }

    best_method = min(methods, key=lambda x: methods[x][0])
    best_mape, best_rmse, best_mae, best_next = methods[best_method]

    description = product_data["description"].iloc[0]
    abc_class = product_data["abc_class"].iloc[0]
    last_week = product_data["week"].iloc[-1]
    last_year = product_data["year"].iloc[-1]
    next_week = last_week + 1 if last_week < 52 else 1
    next_year = last_year if last_week < 52 else last_year + 1

    return {
        "stockcode": stockcode,
        "description": description,
        "abc_class": abc_class,
        "forecast_week": next_week,
        "forecast_year": next_year,
        "ma_forecast": round(max(0, ma_next), 2),
        "exp_forecast": round(max(0, exp_next), 2),
        "reg_forecast": round(max(0, reg_next), 2),
        "best_method": best_method,
        "best_forecast": round(max(0, best_next), 2),
        "mape": best_mape,
        "rmse": best_rmse,
        "mae": best_mae,
        "ma_mape": ma_mape,
        "exp_mape": exp_mape,
        "reg_mape": reg_mape,
    }


def run_forecasting():
    print("=" * 60)
    print("Retail Demand Forecasting — Forecast Engine")
    print("=" * 60)

    weekly, products = load_data()
    eligible_products = products["stockcode"].tolist()

    print(f"Products eligible for forecasting: {len(eligible_products)}")

    results = []
    model_perf = []

    for i, stockcode in enumerate(eligible_products):
        result = forecast_product(stockcode, weekly)
        if result:
            results.append(result)
            model_perf.append({
                "stockcode": stockcode,
                "method": "moving_average",
                "mape": result["ma_mape"],
                "rmse": 0,
                "mae": 0,
                "is_best": 1 if result["best_method"] == "moving_average" else 0
            })
            model_perf.append({
                "stockcode": stockcode,
                "method": "exp_smoothing",
                "mape": result["exp_mape"],
                "rmse": 0,
                "mae": 0,
                "is_best": 1 if result["best_method"] == "exp_smoothing" else 0
            })
            model_perf.append({
                "stockcode": stockcode,
                "method": "regression",
                "mape": result["reg_mape"],
                "rmse": 0,
                "mae": 0,
                "is_best": 1 if result["best_method"] == "regression" else 0
            })

        if (i + 1) % 200 == 0:
            print(f"  Forecasted {i+1}/{len(eligible_products)} products...")

    forecast_df = pd.DataFrame(results)
    perf_df = pd.DataFrame(model_perf)

    conn = sqlite3.connect(DB_PATH)
    forecast_df.to_sql("forecasts", conn, if_exists="replace", index=False)
    perf_df.to_sql("model_performance", conn, if_exists="replace", index=False)

    print(f"\nForecasts generated: {len(forecast_df)}")

    print("\nBest method distribution:")
    print(forecast_df["best_method"].value_counts().to_string())

    print("\nAverage MAPE by ABC class:")
    print(forecast_df.groupby("abc_class")["mape"].mean().round(2).to_string())

    print("\nTop 10 A-class products — forecast next week:")
    top_a = forecast_df[forecast_df["abc_class"] == "A"].nsmallest(10, "mape")
    for _, row in top_a.iterrows():
        print(f"  {row['stockcode']} | {row['description'][:25]} | "
              f"Forecast: {row['best_forecast']:.0f} units | "
              f"Method: {row['best_method']} | MAPE: {row['mape']}%")

    conn.close()
    print("\nForecasting pipeline complete.")
    return forecast_df


if __name__ == "__main__":
    forecast_df = run_forecasting()