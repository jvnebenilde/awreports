from .db import run_query

def get_report_data(start_year: int, end_year: int) -> dict:
    params = [start_year, end_year]

    yearly = run_query("""
        SELECT YEAR(soh.OrderDate) AS [Year],
               CAST(SUM(sod.LineTotal) AS DECIMAL(18,2)) AS Revenue,
               CAST(SUM(sod.OrderQty * p.StandardCost) AS DECIMAL(18,2)) AS Cost,
               CAST(SUM(sod.LineTotal - (sod.OrderQty * p.StandardCost)) AS DECIMAL(18,2)) AS Profit
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY YEAR(soh.OrderDate)
        ORDER BY [Year]
    """, params)

    tot_rev = sum(float(r["Revenue"]) for r in yearly)
    tot_profit = sum(float(r["Profit"]) for r in yearly)
    margin_pct = (tot_profit / tot_rev * 100) if tot_rev else 0.0

    loss_sales = run_query("""
        SELECT COUNT(*) AS loss_count
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
          AND sod.LineTotal < (sod.OrderQty * p.StandardCost)
    """, params)[0]["loss_count"]

    worst_margin = run_query("""
        SELECT TOP 20
               p.Name AS Product,
               CAST(SUM(sod.LineTotal) AS DECIMAL(18,2)) AS Revenue,
               CAST(SUM(sod.OrderQty * p.StandardCost) AS DECIMAL(18,2)) AS Cost,
               CAST(SUM(sod.LineTotal - (sod.OrderQty * p.StandardCost)) AS DECIMAL(18,2)) AS Profit,
               CAST(100.0 * SUM(sod.LineTotal - (sod.OrderQty * p.StandardCost)) / NULLIF(SUM(sod.LineTotal), 0) AS DECIMAL(10,2)) AS MarginPct
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY p.Name
        ORDER BY MarginPct ASC
    """, params)

    monthly = run_query("""
        SELECT FORMAT(soh.OrderDate, 'yyyy-MM') AS Period,
               CAST(SUM(sod.LineTotal) AS DECIMAL(18,2)) AS Revenue,
               CAST(SUM(sod.LineTotal - (sod.OrderQty * p.StandardCost)) AS DECIMAL(18,2)) AS Profit
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY FORMAT(soh.OrderDate, 'yyyy-MM')
        ORDER BY Period
    """, params)

    territory_pl = run_query("""
        SELECT t.Name AS Territory,
               CAST(SUM(sod.LineTotal) AS DECIMAL(18,2)) AS Revenue,
               CAST(SUM(CASE WHEN sod.LineTotal >= (sod.OrderQty * p.StandardCost)
                   THEN sod.LineTotal - (sod.OrderQty * p.StandardCost) ELSE 0 END) AS DECIMAL(18,2)) AS GrossProfit,
               CAST(SUM(CASE WHEN sod.LineTotal < (sod.OrderQty * p.StandardCost)
                   THEN sod.LineTotal - (sod.OrderQty * p.StandardCost) ELSE 0 END) AS DECIMAL(18,2)) AS GrossLoss
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Sales.SalesTerritory t ON t.TerritoryID = soh.TerritoryID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY t.Name
        ORDER BY Revenue DESC
    """, params)

    return {
        "kpis": [
            {"label": "Total Revenue", "value": f"${tot_rev:,.2f}"},
            {"label": "Gross Profit", "value": f"${tot_profit:,.2f}"},
            {"label": "Margin %", "value": f"{margin_pct:.1f}%"},
            {"label": "Loss-Making Sales", "value": f"{loss_sales:,} lines"},
        ],
        "tables": [
            {"title": "Revenue, Cost, and Profit per Year", "rows": yearly},
            {"title": "Worst-Margin Products", "rows": worst_margin},
        ],
        "charts": [
            {
                "id": "revProfitTimeChart",
                "title": "Revenue and Profit Over Time",
                "type": "line",
                "labels": [r["Period"] for r in monthly],
                "datasets": [
                    {"label": "Revenue ($)", "data": [float(r["Revenue"]) for r in monthly]},
                    {"label": "Profit ($)", "data": [float(r["Profit"]) for r in monthly]},
                ],
            },
            {
                "id": "revTerritoryChart",
                "title": "Revenue by Territory",
                "type": "bar",
                "labels": [r["Territory"] for r in territory_pl],
                "datasets": [{"label": "Revenue ($)", "data": [float(r["Revenue"]) for r in territory_pl]}],
            },
            {
                "id": "plTerritoryChart",
                "title": "Profit and Loss by Territory",
                "type": "bar",
                "labels": [r["Territory"] for r in territory_pl],
                "datasets": [
                    {"label": "Profit ($)", "data": [float(r["GrossProfit"]) for r in territory_pl]},
                    {"label": "Loss ($)", "data": [float(r["GrossLoss"]) for r in territory_pl]},
                ],
            },
        ],
    }
