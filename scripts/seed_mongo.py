"""Seed MongoDB Atlas (M0) with a small retail dataset: customers, products, orders.
Keeps well under the 512 MB free-tier limit. Run once from the cloud terminal:
    python scripts/seed_mongo.py --orders 5000
"""
import argparse
import os
import random
from datetime import datetime, timedelta

from dotenv import load_dotenv
from faker import Faker
from pymongo import MongoClient

load_dotenv()
fake = Faker()
Faker.seed(42)
random.seed(42)

CATEGORIES = ["Beverages", "Snacks", "Household", "Personal Care", "Electronics"]
REGIONS = ["North", "Central", "South"]


def make_products(n=60):
    return [
        {
            "_id": f"SKU{1000 + i}",
            "name": fake.unique.word().title() + " " + random.choice(["Pack", "Box", "Bottle", "Unit"]),
            "category": random.choice(CATEGORIES),
            "unit_price": round(random.uniform(1.5, 250.0), 2),
        }
        for i in range(n)
    ]


def make_customers(n=400):
    return [
        {
            "_id": f"CUST{5000 + i}",
            "name": fake.name(),
            "region": random.choice(REGIONS),
            "signup_date": fake.date_time_between(start_date="-2y").isoformat(),
        }
        for i in range(n)
    ]


def make_orders(customers, products, n):
    orders = []
    for i in range(n):
        cust = random.choice(customers)
        n_lines = random.randint(1, 5)
        lines = []
        for _ in range(n_lines):
            p = random.choice(products)
            qty = random.randint(1, 8)
            lines.append({"sku": p["_id"], "qty": qty, "unit_price": p["unit_price"]})
        order_ts = datetime.now() - timedelta(days=random.randint(0, 540))
        orders.append({
            "_id": f"ORD{100000 + i}",
            "customer_id": cust["_id"],
            "region": cust["region"],
            "order_ts": order_ts.isoformat(),
            "status": random.choice(["completed", "completed", "completed", "returned", "cancelled"]),
            "lines": lines,
            "total": round(sum(l["qty"] * l["unit_price"] for l in lines), 2),
        })
    return orders


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", type=int, default=5000)
    args = ap.parse_args()

    client = MongoClient(os.environ["MONGODB_URI"])
    db = client[os.environ.get("MONGO_DB", "retail")]

    products = make_products()
    customers = make_customers()
    orders = make_orders(customers, products, args.orders)

    db.products.drop(); db.customers.drop(); db.orders.drop()
    db.products.insert_many(products)
    db.customers.insert_many(customers)
    db.orders.insert_many(orders)

    print(f"Seeded {len(products)} products, {len(customers)} customers, {len(orders)} orders.")
    print("Storage check:", db.command("dbstats")["dataSize"] / 1e6, "MB (limit is 512 MB)")


if __name__ == "__main__":
    main()
