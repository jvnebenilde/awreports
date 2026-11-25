from .db import run_query

def vendor_purchase_costs():
    return run_query("""
        SELECT TOP 20
               v.Name AS Vendor,
               COUNT(*) AS PurchaseOrders,
               CAST(SUM(poh.TotalDue) AS DECIMAL(18,2)) AS TotalPurchaseCost
        FROM Purchasing.PurchaseOrderHeader poh
        JOIN Purchasing.Vendor v ON v.BusinessEntityID = poh.VendorID
        GROUP BY v.Name
        ORDER BY TotalPurchaseCost DESC
    """)
