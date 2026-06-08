#!/usr/bin/env bash
# Create a $100 monthly budget with email alerts at 50/80/100%.
# Run once, right after `az login`, BEFORE provisioning anything paid.
set -euo pipefail

RG="${1:-rg-bi-agent}"
EMAIL="${2:?Pass your alert email as the 2nd argument}"
SUB=$(az account show --query id -o tsv)
START=$(date -u +%Y-%m-01)
END=$(date -u -d "+1 year" +%Y-%m-01 2>/dev/null || date -u -v+1y +%Y-%m-01)

az consumption budget create \
  --budget-name "bi-agent-monthly" \
  --amount 100 \
  --category Cost \
  --time-grain Monthly \
  --start-date "$START" \
  --end-date "$END" \
  --resource-group "$RG" \
  --notifications "{\"a50\":{\"enabled\":true,\"operator\":\"GreaterThanOrEqualTo\",\"threshold\":50,\"contactEmails\":[\"$EMAIL\"]},\"a80\":{\"enabled\":true,\"operator\":\"GreaterThanOrEqualTo\",\"threshold\":80,\"contactEmails\":[\"$EMAIL\"]},\"a100\":{\"enabled\":true,\"operator\":\"GreaterThanOrEqualTo\",\"threshold\":100,\"contactEmails\":[\"$EMAIL\"]}}"

echo "Budget set on $RG for subscription $SUB. Alerts -> $EMAIL"
echo "If the CLI errors, set the same budget in Portal > Cost Management > Budgets."
