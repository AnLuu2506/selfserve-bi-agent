"""BRONZE: pull raw collections from MongoDB Atlas, write Parquet, upload to ADLS Gen2.
    python scripts/extract_mongo_to_adls.py
Lands one Parquet file per collection under: <filesystem>/raw/<collection>/dt=<YYYY-MM-DD>/.
Orders are exploded to one row per line item so the warehouse layer stays relational.
"""
import os
from datetime import date

import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from azure.storage.filedatalake import DataLakeServiceClient

load_dotenv()
RUN_DT = date.today().isoformat()


def fetch_frames():
    client = MongoClient(os.environ["MONGODB_URI"])
    db = client[os.environ.get("MONGO_DB", "retail")]

    products = pd.DataFrame(list(db.products.find())).rename(columns={"_id": "sku"})
    customers = pd.DataFrame(list(db.customers.find())).rename(columns={"_id": "customer_id"})

    # Explode order line items into a flat fact-like frame.
    orders_raw = list(db.orders.find())
    rows = []
    for o in orders_raw:
        for ln in o["lines"]:
            rows.append({
                "order_id": o["_id"],
                "customer_id": o["customer_id"],
                "region": o["region"],
                "order_ts": o["order_ts"],
                "status": o["status"],
                "sku": ln["sku"],
                "qty": ln["qty"],
                "unit_price": ln["unit_price"],
            })
    order_lines = pd.DataFrame(rows)
    return {"products": products, "customers": customers, "order_lines": order_lines}


def upload(frames):
    svc = DataLakeServiceClient.from_connection_string(os.environ["ADLS_CONNECTION_STRING"])
    fs = svc.get_file_system_client(os.environ.get("ADLS_FILESYSTEM", "bronze"))
    try:
        fs.create_file_system()
    except Exception:
        pass  # already exists

    for name, df in frames.items():
        local = f"/tmp/{name}.parquet"
        df.to_parquet(local, index=False)
        remote = f"raw/{name}/dt={RUN_DT}/{name}.parquet"
        file_client = fs.get_file_client(remote)
        with open(local, "rb") as f:
            file_client.upload_data(f, overwrite=True)
        print(f"uploaded {len(df):>6} rows -> {remote}")


if __name__ == "__main__":
    upload(fetch_frames())
