from django.db import connections

def run_query(sql, params=None):
    """Execute a read-only query against AdventureWorks, return list of dicts."""
    if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
        raise ValueError("Only SELECT queries are allowed.")
    with connections["adventureworks"].cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def get_available_years():
    rows = run_query("SELECT DISTINCT YEAR(OrderDate) AS yr FROM Sales.SalesOrderHeader ORDER BY yr")
    return [r["yr"] for r in rows] or [2011, 2012, 2013, 2014]

