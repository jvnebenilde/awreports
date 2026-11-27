from .db import run_query

def get_report_data(start_year: int, end_year: int) -> dict:
    params = [start_year, end_year]

    kpi_row = run_query("""
        SELECT COUNT(*) AS active_customers,
               COALESCE(SUM(total_spent) / NULLIF(SUM(order_count), 0), 0) AS aov,
               COALESCE(100.0 * SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 0) AS repeat_rate,
               COALESCE(SUM(total_spent), 0) AS grand_total
        FROM (
            SELECT c.CustomerID,
                   COUNT(soh.SalesOrderID) AS order_count,
                   SUM(soh.TotalDue) AS total_spent
            FROM Sales.SalesOrderHeader soh
            JOIN Sales.Customer c ON soh.CustomerID = c.CustomerID
            WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
            GROUP BY c.CustomerID
        ) AS CustSpend
    """, params)[0]

    spenders = run_query("""
        SELECT c.CustomerID,
               COALESCE(s.Name, p.FirstName + ' ' + p.LastName, 'Unknown') AS CustomerName,
               CASE WHEN c.StoreID IS NOT NULL THEN 'Store (B2B)' ELSE 'Individual (B2C)' END AS CustomerType,
               COUNT(soh.SalesOrderID) AS Orders,
               CAST(SUM(soh.TotalDue) AS DECIMAL(18,2)) AS TotalSpent
        FROM Sales.Customer c
        JOIN Sales.SalesOrderHeader soh ON soh.CustomerID = c.CustomerID
        LEFT JOIN Person.Person p ON p.BusinessEntityID = c.PersonID
        LEFT JOIN Sales.Store s ON s.BusinessEntityID = c.StoreID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY c.CustomerID, p.FirstName, p.LastName, s.Name, c.StoreID
        ORDER BY TotalSpent DESC
    """, params)

    top_10 = spenders[:10]
    bottom_10 = list(reversed(spenders[-10:])) if spenders else []
    top_10_sum = sum(float(r["TotalSpent"]) for r in top_10)
    grand_total = float(kpi_row["grand_total"]) or 1.0
    top_10_share = (top_10_sum / grand_total) * 100

    yearly = run_query("""
        SELECT YEAR(soh.OrderDate) AS [Year],
               COUNT(DISTINCT soh.CustomerID) AS ActiveCustomers,
               COUNT(DISTINCT CASE WHEN fo.FirstYear = YEAR(soh.OrderDate) THEN soh.CustomerID END) AS NewCustomers,
               COUNT(DISTINCT CASE WHEN fo.FirstYear < YEAR(soh.OrderDate) THEN soh.CustomerID END) AS ReturningCustomers,
               CAST(SUM(soh.TotalDue) AS DECIMAL(18,2)) AS TotalRevenue
        FROM Sales.SalesOrderHeader soh
        JOIN (
            SELECT CustomerID, MIN(YEAR(OrderDate)) AS FirstYear
            FROM Sales.SalesOrderHeader
            GROUP BY CustomerID
        ) AS fo ON soh.CustomerID = fo.CustomerID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY YEAR(soh.OrderDate)
        ORDER BY [Year]
    """, params) 

    by_type = run_query("""
        SELECT CASE WHEN c.StoreID IS NOT NULL THEN 'Store (Wholesale)' ELSE 'Individual (Retail)' END AS CustomerType,
               CAST(SUM(soh.TotalDue) AS DECIMAL(18,2)) AS Revenue
        FROM Sales.SalesOrderHeader soh
        JOIN Sales.Customer c ON soh.CustomerID = c.CustomerID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY CASE WHEN c.StoreID IS NOT NULL THEN 'Store (Wholesale)' ELSE 'Individual (Retail)' END
    """, params)

    return {
        "kpis": [
            {"label": "Active Customers", "value": f"{kpi_row['active_customers']:,}"},
            {"label": "Average Order Value", "value": f"${kpi_row['aov']:,.2f}"},
            {"label": "Repeat Customer Rate", "value": f"{kpi_row['repeat_rate']:.1f}%"},
            {"label": "Top-10 Revenue Share", "value": f"{top_10_share:.1f}%"},
        ],
        "tables": [
            {"title": "Top 10 Spenders", "rows": top_10},
            {"title": "Bottom 10 Spenders", "rows": bottom_10},
            {"title": "Per-Year Customer Summary", "rows": yearly},
        ],
        "charts": [
            {
                "id": "custNewReturningChart",
                "title": "New vs. Returning Customers per Year",
                "type": "bar",
                "stacked": True,
                "labels": [str(r["Year"]) for r in yearly],
                "datasets": [
                    {"label": "New Customers", "data": [r["NewCustomers"] for r in yearly]},
                    {"label": "Returning Customers", "data": [r["ReturningCustomers"] for r in yearly]},
                ],
            },
            {
                "id": "custTypePieChart",
                "title": "Revenue by Customer Type",
                "type": "doughnut",
                "labels": [r["CustomerType"] for r in by_type],
                "datasets": [{"data": [float(r["Revenue"]) for r in by_type]}],
            },
        ],
    }
