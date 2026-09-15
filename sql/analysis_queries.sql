-- 1. ABC Revenue Summary
SELECT
    abc_class,
    COUNT(*) as product_count,
    ROUND(SUM(total_revenue), 2) as total_revenue,
    ROUND(SUM(total_revenue) * 100.0 / (SELECT SUM(total_revenue) FROM products), 2) as revenue_pct,
    ROUND(AVG(avg_weekly_demand), 1) as avg_weekly_demand
FROM products
GROUP BY abc_class
ORDER BY abc_class;


-- 2. Top 20 products by revenue with forecast
SELECT
    p.stockcode,
    p.description,
    p.abc_class,
    ROUND(p.total_revenue, 2) as total_revenue,
    ROUND(p.avg_weekly_demand, 1) as avg_weekly_demand,
    f.best_forecast as next_week_forecast,
    f.best_method,
    f.mape as forecast_error_pct
FROM products p
JOIN forecasts f ON p.stockcode = f.stockcode
ORDER BY p.total_revenue DESC
LIMIT 20;


-- 3. High risk products requiring immediate action
SELECT
    s.stockcode,
    s.description,
    s.abc_class,
    s.avg_weekly_demand,
    s.forecast_next_week,
    s.safety_stock,
    s.recommended_order_qty,
    s.stockout_risk_score,
    s.risk_level
FROM stockout_risk s
WHERE s.risk_level = 'HIGH'
ORDER BY s.abc_class, s.stockout_risk_score DESC;


-- 4. Forecast accuracy by method
SELECT
    method,
    COUNT(*) as products_where_best,
    ROUND(AVG(mape), 2) as avg_mape
FROM model_performance
WHERE is_best = 1
GROUP BY method
ORDER BY avg_mape;


-- 5. Weekly demand trend — total across all products
SELECT
    year,
    week,
    SUM(total_quantity) as total_units_sold,
    ROUND(SUM(total_revenue), 2) as total_revenue,
    COUNT(DISTINCT stockcode) as active_products,
    ROUND(AVG(total_quantity), 1) as avg_units_per_product
FROM weekly_demand
GROUP BY year, week
ORDER BY year, week;


-- 6. Month over month revenue trend
SELECT
    year,
    week,
    SUM(total_revenue) as weekly_revenue,
    ROUND(AVG(SUM(total_revenue)) OVER (
        ORDER BY year, week
        ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
    ), 2) as rolling_4week_avg,
    ROUND((SUM(total_revenue) - LAG(SUM(total_revenue)) OVER (ORDER BY year, week)) * 100.0 /
        NULLIF(LAG(SUM(total_revenue)) OVER (ORDER BY year, week), 0), 2) as wow_growth_pct
FROM weekly_demand
GROUP BY year, week
ORDER BY year, week;


-- 7. Procurement priority list — what to order this week
SELECT
    s.abc_class,
    s.stockcode,
    s.description,
    ROUND(s.avg_weekly_demand, 0) as avg_weekly_demand,
    s.forecast_next_week,
    s.lead_time_days,
    ROUND(s.safety_stock, 0) as safety_stock,
    ROUND(s.reorder_point, 0) as reorder_point,
    ROUND(s.recommended_order_qty, 0) as order_now,
    s.risk_level
FROM stockout_risk s
WHERE s.recommended_order_qty > 0
    AND s.risk_level IN ('HIGH', 'MEDIUM')
ORDER BY
    CASE s.abc_class WHEN 'A' THEN 1 WHEN 'B' THEN 2 ELSE 3 END,
    s.stockout_risk_score DESC
LIMIT 50;


-- 8. Products with high demand volatility
SELECT
    stockcode,
    description,
    abc_class,
    ROUND(avg_weekly_demand, 1) as avg_demand,
    ROUND(demand_std, 1) as demand_std,
    ROUND(demand_std / NULLIF(avg_weekly_demand, 0) * 100, 1) as coefficient_of_variation_pct
FROM products
WHERE avg_weekly_demand > 10
ORDER BY coefficient_of_variation_pct DESC
LIMIT 20;


-- 9. Best forecasting method by ABC class
SELECT
    f.abc_class,
    f.best_method,
    COUNT(*) as count,
    ROUND(AVG(f.mape), 2) as avg_mape
FROM forecasts f
GROUP BY f.abc_class, f.best_method
ORDER BY f.abc_class, count DESC;


-- 10. Service level analysis
SELECT
    abc_class,
    COUNT(*) as total_products,
    SUM(CASE WHEN risk_level = 'LOW' THEN 1 ELSE 0 END) as low_risk,
    SUM(CASE WHEN risk_level = 'MEDIUM' THEN 1 ELSE 0 END) as medium_risk,
    SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) as high_risk,
    ROUND(SUM(CASE WHEN risk_level = 'HIGH' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as high_risk_pct,
    ROUND(AVG(stockout_risk_score), 2) as avg_risk_score
FROM stockout_risk
GROUP BY abc_class
ORDER BY abc_class;