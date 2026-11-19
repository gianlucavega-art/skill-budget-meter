---
name: invoice-audit
description: Audit a year of supplier invoices: duplicates, missing credit notes, payments without an invoice. Trigger: audit, duplicates
---

# Invoice audit

Load every invoice of the year into one table. Flag duplicate numbers and amounts, credit notes promised but
never issued, and bank payments with no invoice behind them. Output: one list per kind of anomaly.
