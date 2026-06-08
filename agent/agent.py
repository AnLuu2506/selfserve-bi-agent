"""Text-to-SQL chain. Grounds the model in the gold-layer schema, asks for SQL only,
runs it through guardrails, executes against Postgres, and returns rows + the SQL used.
"""
import os

import pandas as pd
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy import create_engine, text

from guardrails import sanitize, UnsafeQuery

# Hand-written schema card. Keep it small and accurate — this is the model's only
# view of the warehouse, and it beats auto-introspection for reliability.
SCHEMA_CARD = """
gold.gold_sales_by_month(order_month DATE, region TEXT, category TEXT,
                         orders INT, units INT, revenue NUMERIC)
gold.gold_top_products(sku TEXT, product_name TEXT, category TEXT,
                       units_sold INT, revenue NUMERIC)
Notes: revenue is from completed orders only. regions are North/Central/South.
Use only these tables. Always alias aggregates with readable names.
"""

SYSTEM = (
    "You are a careful analytics engineer. Given a question, return ONE PostgreSQL "
    "SELECT statement answering it, using only the tables in the schema below. "
    "Return SQL only — no prose, no markdown fences.\n\nSCHEMA:\n{schema}"
)


def _engine():
    url = (
        f"postgresql+psycopg2://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}"
        f"@{os.environ['PGHOST']}:{os.environ.get('PGPORT', '5432')}/{os.environ['PGDATABASE']}"
    )
    return create_engine(url)


def _llm():
    return AzureChatOpenAI(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_key=os.environ["AZURE_OPENAI_API_KEY"],
        api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
        temperature=0,
    )


def answer(question: str):
    """Returns (sql, dataframe). Raises UnsafeQuery if the generated SQL is rejected."""
    prompt = ChatPromptTemplate.from_messages(
        [("system", SYSTEM), ("human", "{q}")]
    )
    raw = (prompt | _llm()).invoke({"schema": SCHEMA_CARD, "q": question}).content
    raw = raw.replace("```sql", "").replace("```", "").strip()
    safe_sql = sanitize(raw)  # raises if unsafe
    with _engine().connect() as conn:
        df = pd.read_sql(text(safe_sql), conn)
    return safe_sql, df
