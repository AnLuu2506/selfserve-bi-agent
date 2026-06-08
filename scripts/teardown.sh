#!/usr/bin/env bash
# Stop the meter. Use `stop` nightly; use `destroy` when the project is done.
set -euo pipefail

RG="${2:-rg-bi-agent}"
VM="${3:-vm-bi-agent}"

case "${1:-stop}" in
  stop)
    # Deallocate releases compute billing (a stopped-but-allocated VM still charges).
    az vm deallocate -g "$RG" -n "$VM"
    echo "VM deallocated. Storage still incurs a few cents/month."
    ;;
  start)
    az vm start -g "$RG" -n "$VM"
    az vm show -d -g "$RG" -n "$VM" --query publicIps -o tsv
    ;;
  destroy)
    read -p "Delete resource group '$RG' and EVERYTHING in it? type yes: " ok
    [ "$ok" = "yes" ] && az group delete -n "$RG" --yes --no-wait && echo "Deleting $RG..."
    ;;
  *)
    echo "usage: $0 {stop|start|destroy} [resource-group] [vm-name]"; exit 1;;
esac

echo "Reminder: also DELETE idle Codespaces (stopped ones still use your 15 GB storage quota)."
