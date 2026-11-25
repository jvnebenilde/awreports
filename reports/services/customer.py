from .db import run_query

def top_customers():
    return run_query("""
        SELECT TOP 20
               c.CustomerID,
               COALESCE(p.FirstName + ' ' + p.LastName, s.Name) AS CustomerName,
               COUNT(soh.SalesOrderID) AS Orders,
               CAST(SUM(soh.TotalDue) AS DECIMAL(18,2)) AS TotalSpent
        FROM Sales.Customer c
        JOIN Sales.SalesOrderHeader soh ON soh.CustomerID = c.CustomerID
        LEFT JOIN Person.Person p ON p.BusinessEntityID = c.PersonID
        LEFT JOIN Sales.Store s ON s.BusinessEntityID = c.StoreID
        GROUP BY c.CustomerID, p.FirstName, p.LastName, s.Name
        ORDER BY TotalSpent DESC
    """)
