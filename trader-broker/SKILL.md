---
name: trader-broker
description: "Order executor and broker connector for Indian stocks (NSE/BSE). Provides paper trading simulation, Zerodha / Angel One / Groww / Dhan payloads, and guarantees strict human approval before order dispatch."
---

# Order Executor (`trader-broker`)

Coordinates simulated paper execution and formats ready-to-dispatch API payloads for leading Indian brokers.

## Safety Controls
- **Cryptographic Fingerprint Check**: Verifies that the order has passed `trader-risk` checks without tampering.
- **Explicit Human Confirmation Required**: Requires explicit confirmation (`--confirm "yes"`) before executing any order.
- **Paper Trading by Default**: Safeguards your capital by tracking paper fills in `trader/state/portfolio.json`.

## Supported Brokers
- **Zerodha Kite Connect**: Intraday MIS Limit and SL-M order payloads.
- **Angel One SmartAPI**: Intraday order payload.
- **Dhan HQ API**: Intraday orders.
- **Generic Webhook / JSON**: Connects to algorithmic trading webhooks.

## CLI Usage

```bash
# Display pending tickets and readiness status
python3 trader-broker/ticket.py show

# Execute paper trade (requires confirmation)
python3 trader-broker/ticket.py execute --confirm "yes"

# Generate broker code/payload for live execution
python3 trader-broker/ticket.py export --broker zerodha
python3 trader-broker/ticket.py export --broker angelone

# Check paper portfolio, LTP, and active P&L
python3 trader-broker/ticket.py status

# Square off all open intraday positions
python3 trader-broker/ticket.py squareoff --confirm "yes"
```
