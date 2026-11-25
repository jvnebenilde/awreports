from .db import run_query

def revenue_by_territory():
    return run_query("""
        SELECT t.Name AS Territory, t.[Group] AS RegionGroup,
               CAST(SUM(soh.SubTotal) AS DECIMAL(18,2)) AS Revenue
        FROM Sales.SalesOrderHeader soh
        JOIN Sales.SalesTerritory t ON t.TerritoryID = soh.TerritoryID
        GROUP BY t.Name, t.[Group]
        ORDER BY Revenue DESC
    """)
