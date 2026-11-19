---
name: invoice-checker
description: Check a supplier invoice against the quote and the order: totals, unit prices, VAT, quantities. Trigger: invoice, quote, overcharge
---

# Invoice checker

Compare each invoice line with the matching quote line. Recompute totals and VAT with a script, never by hand.
Flag unit prices above the quote, quantities above the order and lines with no quote behind them.
Output: a table of differences and the amount to dispute.
