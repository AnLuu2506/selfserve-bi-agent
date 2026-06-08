"""Load the latest bronze Parquet from ADLS into Postgres `bronze` schema.
dbt then transforms bronze -> silver -> gold inside Postgres.
    python scripts/load_bronze_to_postgres.py
"""
import io
import os
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from azure.storage.filedatalake import DataLakeServiceClient

load_dotenv()
RUN_DT = date.today().isoformat()
COLLECTIONS = ["products", "customers", "order_lines"]


def pg_engine():
    url = (
        f"postgresql+psycopg2://{os.environ['PGUSER']}:{os.environ['PGPASSWORD']}"
        f"@{os.environ['PGHOST']}:{os.environ.get('PGPORT', '5432')}/{os.environ['PGDATABASE']}"
    )
    return create_engine(url)


def main():
    svc = DataLakeServiceClient.from_connection_string(os.environ["ADLS_CONNECTION_STRING"])
    fs = svc.get_file_system_client(os.environ.get("ADLS_FILESYSTEM", "bronze"))
    engine = pg_engine()

    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS bronze"))

    for name in COLLECTIONS:
        remote = f"raw/{name}/dt={RUN_DT}/{name}.parquet"
        data = fs.get_file_client(remote).download_file().readall()
        df = pd.read_parquet(io.BytesIO(data))
        df.to_sql(name, engine, schema="bronze", if_exists="replace", index=False)
        print(f"loaded {len(df):>6} rows -> bronze.{name}")


if __name__ == "__main__":
    main()
