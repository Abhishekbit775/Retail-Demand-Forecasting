# Retail Demand Forecasting

Demand forecasting and procurement recommendation engine built on 541,909 real retail transactions from a UK online retailer. Forecasts weekly product demand, flags stockout risk, and generates specific order quantities for procurement teams.

The goal was to move beyond just predicting sales â€” the system tells you what to actually order and when.

---

## Background

Started with raw transactional data from the UCI Online Retail dataset. The messiness was real â€” cancellations mixed with regular orders, non-product charges like postage and bank fees, negative quantities from returns, and inconsistent stock codes.

The interesting engineering problem was building a forecasting system that handles 3,805 different products with varying demand patterns â€” some sell 900 units a week, some sell 5. A single forecasting method does not work for all of them.

---

## What it does

Cleans and structures raw transaction data
Removes cancellations (invoices starting with C), returns (negative quantities), and non-product entries. Engineers weekly demand aggregates per product. Applies ABC classification to segment products by revenue contribution.

Forecasts next week demand per product
Runs three methods per product â€” Moving Average (baseline), Exponential Smoothing (weights recent data more), and Linear Regression (captures trend). Selects the best method per product based on lowest MAPE on a 4-week holdout test. No single method is forced on all products.

Generates procurement recommendations
For each product computes safety stock, reorder point, and recommended order quantity using lead time, demand volatility, and service level targets that vary by ABC class. Outputs a prioritized procurement list with risk levels.

---

## ABC Classification

Pareto principle working exactly as expected on real data:

Class A: 914 products, Â£8,225,109 revenue (80% of total), 196.7 units/week average
Class B: 1,053 products, Â£1,543,697 revenue (15% of total), 39.4 units/week average  
Class C: 2,069 products, Â£514,437 revenue (5% of total), 13.6 units/week average

A-class products get shortest lead time assumption (3 days), highest service level target (95%, Z=1.65), and priority in the procurement list. C-class gets 7-day lead time and 80% service level â€” over-engineering low-revenue products wastes capital.

---

## Forecasting Results

Products forecasted: 3,149 (products with at least 8 weeks of history)

Best method distribution:
Moving Average won for 38% of products
Exponential Smoothing won for 36% of products
Linear Regression won for 26% of products

No single method dominated â€” validates the multi-method approach.

Best A-class products achieved 3-10% MAPE on the holdout test.
Overall average MAPE is high (~180%) because retail demand has genuine noise â€” bulk corporate orders can triple a week's sales randomly. The products that matter for business decisions have much lower error rates.

---

## Procurement Output

Total recommendations generated: 3,430
High risk products: 229 (need immediate attention)
Medium risk: 1,990
Low risk: 1,211

High risk A-class breakdown:
8% of A-class products flagged as high stockout risk.
Top urgent item: RAIN PONCHO RETROSPOT â€” 136 units recommended order, 138 units safety stock.

---

## Key formulas

Safety Stock = Z Ã— daily_demand_std Ã— sqrt(lead_time_days)
Reorder Point = (daily_demand Ã— lead_time_days) + safety_stock
Recommended Order = (forecast Ã— lead_time_days/7) + safety_stock - current_inventory_proxy

Service level Z values:
A-class: Z=1.65 (95% service level)
B-class: Z=1.28 (90% service level)
C-class: Z=1.04 (85% service level)

---

## Database Schema

5-table SQLite schema:

products â€” dimension table, one row per product with ABC class and demand stats
weekly_demand â€” fact table, one row per product per week
forecasts â€” all three method forecasts + best method selection + accuracy metrics
stockout_risk â€” procurement recommendations with risk scores and order quantities
model_performance â€” per-product per-method accuracy for benchmarking

---

## Stack

Python, Pandas, NumPy, Statsmodels (Exponential Smoothing), Scikit-learn (Linear Regression), SQLite, Matplotlib, Seaborn

---

## Limitations

Current inventory is a proxy (1.5x average weekly demand) since actual warehouse data is not available. Real inventory levels would make recommendations significantly more precise.

Lead times are assumptions by ABC class, not actual supplier lead time data.

Regression-based forecasting does not model seasonality explicitly. This dataset has clear December peaks that a seasonal decomposition model would capture better.

MAPE is a noisy metric for retail demand with occasional bulk orders. MAE on filtered regular orders would be more meaningful for business decisions.

---

## How to run

git clone https://github.com/Abhishekbit775/Retail-Demand-Forecasting.git
cd Retail-Demand-Forecasting

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Add online_retail.xlsx to data/raw/ then run in order:
python3 src/clean.py
python3 src/load_to_db.py
python3 src/forecast.py
python3 src/recommend.py

---

## Structure

data/raw/          â€” original Excel file, not committed
data/processed/    â€” cleaned CSV and weekly demand table
sql/               â€” schema and 10 analysis queries
src/               â€” pipeline scripts
dashboard/         â€” output plots