from .db import run_query, format_kpi

def get_report_data(start_year: int, end_year: int) -> dict:
    params = [start_year, end_year]

    kpi_base = run_query("""
        SELECT COALESCE(SUM(TotalDue), 0) AS total_sales,
               COUNT(SalesOrderID) AS total_orders
        FROM Sales.SalesOrderHeader
        WHERE YEAR(OrderDate) BETWEEN %s AND %s
    """, params)[0]

    top_terr = run_query("""
        SELECT TOP 1 st.Name AS name
        FROM Sales.SalesOrderHeader soh
        JOIN Sales.SalesTerritory st ON soh.TerritoryID = st.TerritoryID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY st.Name
        ORDER BY SUM(soh.TotalDue) DESC
    """, params)

    best_prod = run_query("""
        SELECT TOP 1 p.Name AS name
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY p.Name
        ORDER BY SUM(sod.OrderQty) DESC
    """, params)

    sales_by_year = run_query("""
        SELECT YEAR(OrderDate) AS [Year],
               COUNT(SalesOrderID) AS Orders,
               CAST(SUM(SubTotal) AS DECIMAL(18,2)) AS SubTotal,
               CAST(SUM(TaxAmt + Freight) AS DECIMAL(18,2)) AS TaxAndFreight,
               CAST(SUM(TotalDue) AS DECIMAL(18,2)) AS TotalSales
        FROM Sales.SalesOrderHeader
        WHERE YEAR(OrderDate) BETWEEN %s AND %s
        GROUP BY YEAR(OrderDate)
        ORDER BY [Year]
    """, params)

    top_products = run_query("""
        SELECT TOP 25
               p.Name AS Product,
               COALESCE(pc.Name, 'Uncategorized') AS Category,
               COALESCE(psc.Name, 'General') AS Subcategory,
               SUM(sod.OrderQty) AS UnitsSold,
               CAST(SUM(sod.LineTotal) AS DECIMAL(18,2)) AS Revenue
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        LEFT JOIN Production.ProductSubcategory psc ON p.ProductSubcategoryID = psc.ProductSubcategoryID
        LEFT JOIN Production.ProductCategory pc ON psc.ProductCategoryID = pc.ProductCategoryID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY p.Name, pc.Name, psc.Name
        ORDER BY Revenue DESC
    """, params)

    monthly = run_query("""
        SELECT FORMAT(OrderDate, 'yyyy-MM') AS Period,
               CAST(SUM(TotalDue) AS DECIMAL(18,2)) AS TotalSales
        FROM Sales.SalesOrderHeader
        WHERE YEAR(OrderDate) BETWEEN %s AND %s
        GROUP BY FORMAT(OrderDate, 'yyyy-MM')
        ORDER BY Period
    """, params)

    territory = run_query("""
        SELECT st.[Group] AS RegionGroup,
               st.Name AS Territory,
               CAST(SUM(soh.TotalDue) AS DECIMAL(18,2)) AS TotalSales
        FROM Sales.SalesOrderHeader soh
        JOIN Sales.SalesTerritory st ON soh.TerritoryID = st.TerritoryID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY st.[Group], st.Name
        ORDER BY TotalSales DESC
    """, params)

    category = run_query("""
        SELECT COALESCE(pc.Name, 'Other') AS Category,
               COALESCE(psc.Name, 'Other') AS Subcategory,
               CAST(SUM(sod.LineTotal) AS DECIMAL(18,2)) AS TotalSales
        FROM Sales.SalesOrderDetail sod
        JOIN Sales.SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
        JOIN Production.Product p ON sod.ProductID = p.ProductID
        LEFT JOIN Production.ProductSubcategory psc ON p.ProductSubcategoryID = psc.ProductSubcategoryID
        LEFT JOIN Production.ProductCategory pc ON psc.ProductCategoryID = pc.ProductCategoryID
        WHERE YEAR(soh.OrderDate) BETWEEN %s AND %s
        GROUP BY pc.Name, psc.Name
        ORDER BY TotalSales DESC
    """, params)

    return {
        "kpis": [
            {"label": "Total Sales", "value": format_kpi(kpi_base["total_sales"], prefix="$")},
            {"label": "Orders", "value": format_kpi(kpi_base["total_orders"])},
            {"label": "Top Territory", "value": top_terr[0]["name"] if top_terr else "N/A"},
            {"label": "Best-Selling Product", "value": best_prod[0]["name"] if best_prod else "N/A"},
        ], 
        "tables": [
            {"title": "Total Sales by Year", "rows": sales_by_year},
            {"title": "Top Products & Categories", "rows": top_products},
        ],
        "charts": [
            {
                "id": "salesMonthlyChart",
                "title": "Sales Over Time (Monthly)",
                "type": "line",
                "labels": [r["Period"] for r in monthly],
                "datasets": [{"label": "Sales ($)", "data": [float(r["TotalSales"]) for r in monthly]}],
            },
            {
                "id": "salesTerritoryBar",
                "title": "Sales by Territory",
                "type": "bar",
                "labels": [r["Territory"] for r in territory],
                "datasets": [{"label": "Sales ($)", "data": [float(r["TotalSales"]) for r in territory]}],
            },
            {
                "id": "salesTerritoryRegionPie",
                "title": "Sales by Territory & Region",
                "type": "pie",
                "labels": [f"{r['RegionGroup']} - {r['Territory']}" for r in territory],
                "datasets": [{"data": [float(r["TotalSales"]) for r in territory]}],
            },
            {
                "id": "salesCategoryPie",
                "title": "Sales by Category & Subcategory",
                "type": "pie",
                "labels": [f"{r['Category']} / {r['Subcategory']}" for r in category],
                "datasets": [{"data": [float(r["TotalSales"]) for r in category]}],
            },
        ],
    }

