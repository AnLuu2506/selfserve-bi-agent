"""Safety layer for the text-to-SQL agent. The LLM proposes SQL; nothing runs
until it passes these checks. This is the part interviewers care about.
"""
import re

ALLOWED_SCHEMAS = {"gold"}
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|merge)\b",
    re.IGNORECASE,
)
MAX_ROWS = 1000


class UnsafeQuery(Exception):
    pass


def sanitize(sql: str) -> str:
    """Validate the model's SQL and enforce a row cap. Raises UnsafeQuery on violation."""
    cleaned = sql.strip().rstrip(";").strip()

    if ";" in cleaned:
        raise UnsafeQuery("Multiple statements are not allowed.")
    if not cleaned.lower().startswith(("select", "with")):
        raise UnsafeQuery("Only SELECT/CTE queries are allowed.")
    if FORBIDDEN.search(cleaned):
        raise UnsafeQuery("Write/DDL keywords are not allowed.")

    # Every schema-qualified reference must live in an allowlisted schema.
    for schema in re.findall(r"\b(\w+)\.\w+", cleaned):
        if schema not in ALLOWED_SCHEMAS:
            raise UnsafeQuery(f"Schema '{schema}' is not queryable. Allowed: {ALLOWED_SCHEMAS}.")

    if not re.search(r"\blimit\b", cleaned, re.IGNORECASE):
        cleaned += f"\nLIMIT {MAX_ROWS}"
    return cleaned
