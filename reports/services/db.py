from django.db import connections
import math
from decimal import Decimal

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

def format_kpi(value, prefix="", suffix=""):
    """Format a number to 4 significant digits with K/M/B/T suffixes."""
    if value is None:
        return f"{prefix}0{suffix}"

    num = float(value)
    sign = "-" if num < 0 else ""
    num = abs(num)

    if num < 1_000:
        if num == int(num):
            return f"{sign}{prefix}{int(num)}{suffix}"
        # Keep up to 4 significant digits for values under 1,000
        digits = int(math.floor(math.log10(num))) + 1 if num > 0 else 1
        decimals = max(0, 4 - digits)
        factor = 10 ** decimals
        truncated = math.floor(num * factor) / factor
        formatted = f"{truncated:.{decimals}f}".rstrip("0").rstrip(".")
        return f"{sign}{prefix}{formatted}{suffix}"

    units = [(1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")]
    for threshold, unit in units:
        if num >= threshold:
            scaled = num / threshold
            int_digits = len(str(int(scaled)))  # 1, 2, or 3
            decimals = max(0, 4 - int_digits)
            factor = 10 ** decimals
            truncated = math.floor(scaled * factor) / factor
            formatted = f"{truncated:.{decimals}f}".rstrip("0").rstrip(".")
            return f"{sign}{prefix}{formatted}{unit}{suffix}"


