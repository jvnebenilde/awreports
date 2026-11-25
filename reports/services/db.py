from django.db import connections

def run_query(sql, params=None):
    """Execute a read-only query against AdventureWorks, return list of dicts."""
    if not sql.lstrip().upper().startswith(("SELECT", "WITH")):
        raise ValueError("Only SELECT queries are allowed.")
    with connections["adventureworks"].cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
