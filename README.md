# Self-Serve BI Platform + Analytics Agent — 1-Month Build Guide

A month-long, cloud-hosted build for a self-serve BI platform with a natural-language
analytics agent. **Stack philosophy:** open-source tooling as the core, Microsoft/Azure
as the cloud and AI layer, MongoDB as the operational source. Everything runs in the
cloud so an 8 GB laptop is never the bottleneck — you code in a browser IDE and the
platform lives on Azure.

```
MongoDB Atlas (M0, source docs)
        │  pymongo extract
        ▼
Azure Data Lake Gen2  ── raw Parquet ──►  Postgres warehouse (on Azure VM)
   (BRONZE)                                   │  dbt-core
                                              ▼
                                   SILVER  →  GOLD marts
                                              │
                        ┌─────────────────────┴───────────────────┐
                        ▼                                          ▼
                Metabase (self-serve BI UI)        Streamlit + LangChain agent
                                                   (text-to-SQL on Azure OpenAI)

Dev IDE:  GitHub Codespaces (VSCode in browser + terminal)
CI:       GitHub Actions   |   Orchestration: cron (Airflow optional)
```

## Why this shape
- **Open-source core:** dbt-core, Postgres, Metabase, Streamlit, LangChain — the skills transfer to any employer and there is nothing to un-learn.
- **Microsoft layer:** Azure VM + ADLS Gen2 host it; GitHub Codespaces is your cloud IDE; Azure OpenAI is the agent's brain. This is the muscle MNC/FMCG shops want.
- **MongoDB source:** a realistic "operational store → analytics" flow, exactly the seam most BI platforms start from. M0 is free on Azure with 512 MB.

## Cost expectation
Designed to run on the **Azure $200 free credit (first 30 days)** — which lines up exactly
with this 1-month project — with **$100 as a safety buffer, not a target**. Realistic
out-of-pocket if you deallocate the VM nightly: near zero.

| Component | Tier | Cost |
|---|---|---|
| MongoDB Atlas M0 | Free forever, on Azure | $0 |
| GitHub Codespaces | 120 core-hrs + 15 GB/mo (personal) | $0 if you stay under |
| Azure VM B2ms (2 vCPU/8 GB) | PAYG, deallocate when idle | ~$0.083/hr → ~$15–25 for the month |
| ADLS Gen2 storage | a few GB of Parquet | cents |
| Azure OpenAI (gpt-4o-mini) | pay per token | a few $ |
| Metabase / Postgres / dbt / Streamlit | open-source | $0 |

> **The budget only dies from forgotten resources.** Run `scripts/azure_budget_alert.sh`
> on day 1, `scripts/teardown.sh stop` every night, and **delete idle Codespaces**
> (a stopped Codespace still burns your 15 GB storage quota).

---

## Prerequisites (all free, ~30 min)
1. **GitHub account** (personal — Codespaces free tier only applies to personal accounts).
2. **Azure free account** — $200 credit / 30 days. Card needed for identity only.
3. **MongoDB Atlas account** — sign up at cloud.mongodb.com, no card needed.
4. **Azure OpenAI access** — create an Azure OpenAI resource and deploy `gpt-4o-mini`.

---

## Week 1 — Foundations & cloud dev environment

### 1.1 Get the repo into Codespaces (your cloud UI + terminal)
1. Create a new GitHub repo, push this scaffold to it (or fork it).
2. On the repo page: **Code ▸ Codespaces ▸ Create codespace on main**.
3. Codespaces boots VSCode in your browser with an integrated terminal. The
   `.devcontainer/devcontainer.json` auto-installs Python, Azure CLI, Docker, and
   `requirements.txt`. This is where you do *all* coding for the month.
4. Set the idle timeout low: **Settings ▸ Codespaces ▸ Default idle timeout = 10 min**
   so you don't bleed core-hours.

### 1.2 Stand up MongoDB Atlas (source)
1. cloud.mongodb.com ▸ **Create ▸ M0 Free** ▸ provider **Azure**, region nearest you (e.g. East Asia / Southeast Asia).
2. **Database Access:** create a user + password. **Network Access:** add `0.0.0.0/0` (dev only).
3. **Connect ▸ Drivers** → copy the `mongodb+srv://...` string.
4. In the Codespaces terminal: `cp .env.example .env` and paste `MONGODB_URI`.
5. Seed it: `python scripts/seed_mongo.py --orders 5000` → check it prints well under 512 MB.

### 1.3 Provision Azure (host + storage)
In the Codespaces terminal:
```bash
az login --use-device-code
az group create -n rg-bi-agent -l southeastasia

# BUDGET FIRST — before anything paid:
bash scripts/azure_budget_alert.sh rg-bi-agent you@example.com

# Storage account + Data Lake (Bronze):
az storage account create -n myadls$RANDOM -g rg-bi-agent -l southeastasia \
  --sku Standard_LRS --hns true       # hns=true makes it ADLS Gen2
# Grab the connection string into .env as ADLS_CONNECTION_STRING:
az storage account show-connection-string -g rg-bi-agent -n <account> -o tsv
```

### 1.4 Provision the VM that hosts the platform
```bash
az vm create -g rg-bi-agent -n vm-bi-agent --image Ubuntu2204 \
  --size Standard_B2ms --admin-username azureuser --generate-ssh-keys
# open the service ports
az vm open-port -g rg-bi-agent -n vm-bi-agent --port 3000 --priority 1001  # Metabase
az vm open-port -g rg-bi-agent -n vm-bi-agent --port 8501 --priority 1002  # Agent
az vm show -d -g rg-bi-agent -n vm-bi-agent --query publicIps -o tsv       # note the IP
```
SSH in, install Docker, clone the repo:
```bash
ssh azureuser@<VM_IP>
curl -fsSL https://get.docker.com | sh && sudo usermod -aG docker $USER && exit
ssh azureuser@<VM_IP>   # re-login for group change
git clone <your-repo> && cd selfserve-bi-agent && cp .env.example .env  # fill it in
```

**Week 1 done when:** Codespaces opens, Atlas has 5k orders, Azure RG + budget + storage + VM exist.

---

## Week 2 — The data platform (Bronze → Silver → Gold)

### 2.1 Bronze: MongoDB → ADLS (run from Codespaces)
```bash
python scripts/extract_mongo_to_adls.py     # writes raw/<collection>/dt=.../*.parquet
```

### 2.2 Warehouse up + load Bronze (on the VM)
```bash
docker compose up -d postgres          # Postgres warehouse
python scripts/load_bronze_to_postgres.py   # ADLS Parquet -> bronze.* tables
```

### 2.3 Silver + Gold with dbt
```bash
cp dbt/selfserve/profiles.example.yml ~/.dbt/profiles.yml
cd dbt/selfserve
dbt debug          # confirms the Postgres connection
dbt build          # staging (views) -> silver (tables) -> gold marts
dbt docs generate  # lineage + the schema you'll screenshot for your portfolio
```
You now have `gold.gold_sales_by_month` and `gold.gold_top_products`.

### 2.4 Orchestrate (keep it light)
For a learning project, a cron entry on the VM is enough and won't eat your 8 GB:
```bash
# crontab -e  — refresh the whole pipeline every morning at 6am
0 6 * * * cd ~/selfserve-bi-agent && python scripts/extract_mongo_to_adls.py && \
          python scripts/load_bronze_to_postgres.py && \
          cd dbt/selfserve && dbt build >> ~/pipeline.log 2>&1
```
**Stretch (Week 4):** swap cron for Airflow `LocalExecutor` (single container — far lighter
than Celery+Redis) to show orchestration skills. Don't run full Celery Airflow on a B2ms.

**Week 2 done when:** `dbt build` is green and gold tables hold sensible numbers.

---

## Week 3 — Self-serve BI + the agent

### 3.1 Metabase (the self-serve UI)
```bash
docker compose up -d metabase          # http://<VM_IP>:3000
```
First-run wizard → connect to the Postgres warehouse (host `postgres`, db `warehouse`).
Build 3–4 dashboards off the **gold** schema (revenue trend, region split, top products).
Metabase's own "Ask a question" gives non-technical users self-serve drill-down without code.

### 3.2 The text-to-SQL agent
The agent (`agent/`) is the part that wins interviews because *you built the brain*, not a toggle:
- `agent/agent.py` — grounds Azure OpenAI in a hand-written **schema card** (more reliable than auto-introspection at this scale), asks for SQL only.
- `agent/guardrails.py` — rejects anything that isn't a read-only `SELECT` on the `gold` schema and caps rows. **Always show the SQL it ran** (the app does this in an expander) — transparency is the whole point.
- `agent/app.py` — Streamlit UI with example questions and an auto-chart.

Fill the `AZURE_OPENAI_*` values in `.env`, then:
```bash
docker compose up -d agent             # http://<VM_IP>:8501
# or, to iterate in Codespaces:  streamlit run agent/app.py
```
Test: *"Top 5 products by revenue"*, *"revenue by region last quarter"*,
*"which category grew the most month over month"*, and one out-of-scope question to
confirm it declines gracefully.

**Week 3 done when:** a non-technical question returns a correct answer **and** the SQL.

---

## Week 4 — Harden, document, ship

1. **CI:** push triggers `.github/workflows/dbt-ci.yml` (sqlfluff lint + `dbt parse` on a throwaway Postgres). Get a green check.
2. **Evals:** write 8–10 question/expected-SQL pairs; assert the agent's SQL returns the right shape. This is your "AI quality" story.
3. **Observability:** log every question → generated SQL → row count → latency to a `gold.agent_log` table; build a tiny Metabase dashboard on it.
4. **Docs for the portfolio:** the lineage from `dbt docs`, an architecture diagram (the ASCII one above is a fine start), and a 1-page write-up framed for a hiring manager.
5. **Demo + teardown:** record a 3-minute walkthrough, then `bash scripts/teardown.sh destroy` (or `stop` if you'll keep iterating). **Delete the Codespace too.**

---

## Daily cost hygiene (do this without fail)
```bash
bash scripts/teardown.sh stop      # deallocate the VM every night
# delete idle Codespaces at github.com/codespaces — stopped ones still use storage
az consumption usage list --query "[].{name:instanceName,cost:pretaxCost}" -o table
```

## What you'll be able to say in an interview
- Built an end-to-end medallion lakehouse from a **MongoDB** source on **Azure**, transformed with **dbt**, served via **Metabase**.
- Shipped a **text-to-SQL agent** on **Azure OpenAI** with explicit **guardrails and evals** — not a vendor toggle.
- Ran the whole thing **cloud-native** (Codespaces + Azure VM) with **budget controls and CI**.

This maps directly onto DP-700 (lakehouse, medallion, pipelines) and AI-fundamentals territory,
and it's a single coherent artifact you can demo live.
