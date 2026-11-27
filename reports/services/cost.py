from .db import run_query, format_kpi

def get_report_data(start_year: int, end_year: int) -> dict:
    params = [start_year, end_year]

    cogs = float(run_query("""
        SELECT COALESCE(SUM(sod.OrderQty * p.StandardCost), 0) AS cogs
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
    """, params)[0]["cogs"])

    purch_spend = float(run_query("""
        SELECT COALESCE(SUM(TotalDue), 0) AS spend
        FROM Purchasing.PurchaseOrderHeader
        WHERE YEAR(OrderDate) BETWEEN %s AND %s
    """, params)[0]["spend"])

    mfg_cost = float(run_query("""
        SELECT COALESCE(SUM(ActualCost), 0) AS mfg
        FROM Production.WorkOrderRouting
        WHERE YEAR(ActualStartDate) BETWEEN %s AND %s
    """, params)[0]["mfg"])

    top_vendors = run_query("""
        SELECT TOP 20
               v.Name AS Vendor,
               COUNT(*) AS PurchaseOrders,
               CAST(SUM(poh.TotalDue) AS DECIMAL(18,2)) AS TotalPurchaseCost
        FROM Purchasing.PurchaseOrderHeader poh
        JOIN Purchasing.Vendor v ON v.BusinessEntityID = poh.VendorID
        WHERE YEAR(poh.OrderDate) BETWEEN %s AND %s
        GROUP BY v.Name
        ORDER BY TotalPurchaseCost DESC
    """, params)

    top_cost_products = run_query("""
        SELECT TOP 20
               p.Name AS Product,
               SUM(sod.OrderQty) AS UnitsSold,
               CAST(p.StandardCost AS DECIMAL(18,2)) AS UnitCost,
               CAST(SUM(sod.OrderQty * p.StandardCost) AS DECIMAL(18,2)) AS TotalCost
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY p.Name, p.StandardCost
        ORDER BY TotalCost DESC
    """, params)

    cost_per_year = run_query("""
        SELECT y.yr AS [Year],
               COALESCE(c.cogs, 0) AS COGS,
               COALESCE(p.purch, 0) AS PurchasingSpend,
               COALESCE(m.mfg, 0) AS ManufacturingCost,
               CAST(COALESCE(c.cogs, 0) + COALESCE(p.purch, 0) + COALESCE(m.mfg, 0) AS DECIMAL(18,2)) AS TotalCost
        FROM (
            SELECT DISTINCT YEAR(OrderDate) AS yr FROM Sales.SalesOrderHeader WHERE YEAR(OrderDate) BETWEEN %s AND %s
        ) y
        LEFT JOIN (
            SELECT YEAR(soh.OrderDate) AS yr, CAST(SUM(sod.OrderQty * pr.StandardCost) AS DECIMAL(18,2)) AS cogs
            FROM Sales.SalesOrderDetail sod
            JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
            JOIN Production.Product pr ON sod.ProductID = pr.ProductID
            GROUP BY YEAR(soh.OrderDate)
        ) c ON y.yr = c.yr
        LEFT JOIN (
            SELECT YEAR(OrderDate) AS yr, CAST(SUM(TotalDue) AS DECIMAL(18,2)) AS purch
            FROM Purchasing.PurchaseOrderHeader
            GROUP BY YEAR(OrderDate)
        ) p ON y.yr = p.yr
        LEFT JOIN (
            SELECT YEAR(ActualStartDate) AS yr, CAST(SUM(ActualCost) AS DECIMAL(18,2)) AS mfg
            FROM Production.WorkOrderRouting
            GROUP BY YEAR(ActualStartDate)
        ) m ON y.yr = m.yr
        ORDER BY y.yr
    """, params)

    monthly_cost = run_query("""
        SELECT FORMAT(soh.OrderDate, 'yyyy-MM') AS Period,
               CAST(SUM(sod.OrderQty * p.StandardCost) AS DECIMAL(18,2)) AS COGS
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY FORMAT(soh.OrderDate, 'yyyy-MM')
        ORDER BY Period
    """, params)

    largest_item = top_cost_products[0]["Product"] if top_cost_products else "N/A"

    return {
        "kpis": [
            {"label": "Cost of Goods Sold", "value": format_kpi(cogs, prefix="$")},
            {"label": "Purchasing Spend", "value": format_kpi(purch_spend, prefix="$")},
            {"label": "Manufacturing Cost", "value": format_kpi(mfg_cost, prefix="$")},
            {"label": "Largest Single Cost Item", "value": largest_item},
        ], 
        "tables": [
            {"title": "Cost per Year", "rows": cost_per_year},
            {"title": "Top Vendors", "rows": top_vendors},
            {"title": "Top-Cost Products", "rows": top_cost_products},
        ],
        "charts": [
            {
                "id": "costOverTimeChart",
                "title": "Cost Over Time (Month)",
                "type": "line",
                "labels": [r["Period"] for r in monthly_cost],
                "datasets": [{"label": "COGS ($)", "data": [float(r["COGS"]) for r in monthly_cost]}],
            },
            {
                "id": "topVendorsChart",
                "title": "Top Vendors by Spend",
                "type": "bar",
                "horizontal": True,
                "labels": [r["Vendor"] for r in top_vendors[:10]],
                "datasets": [{"label": "Spend ($)", "data": [float(r["TotalPurchaseCost"]) for r in top_vendors[:10]]}],
            },
            {
                "id": "topProductsCostChart",
                "title": "Top Products by Cost",
                "type": "bar",
                "horizontal": True,
                "labels": [r["Product"] for r in top_cost_products[:10]],
                "datasets": [{"label": "Total Cost ($)", "data": [float(r["TotalCost"]) for r in top_cost_products[:10]]}],
            },
        ],
    }

