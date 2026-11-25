from .db import run_query

def monthly_sales():
    return run_query("""
        SELECT YEAR(OrderDate) AS [Year], MONTH(OrderDate) AS [Month],
               COUNT(*) AS Orders, SUM(TotalDue) AS TotalSales
        FROM Sales.SalesOrderHeader
        GROUP BY YEAR(OrderDate), MONTH(OrderDate)
        ORDER BY [Year], [Month]
    """)
