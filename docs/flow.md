# Flow Maps

This page illustrates the end-to-end runtime with simplified flow and sequence diagrams.

## Table of Contents
- High-level flowchart
- Sequence of a live trade
- Notes on signals and filters

```mermaid
flowchart TD
  A[Start] --> B[Load .env]
  B --> C[KrakenAPI Init]
  C --> D{Verify balances}
  D -->|USDC/XRP found| E[Select pairs]
  E --> F[Scanner Loop]
  F --> G{Signals?}
  G -->|Yes| H[Execute Trade]
  G -->|No| F
  H --> I[Log + PnL]
  I --> F
```

```mermaid
sequenceDiagram
  participant User
  participant Trader
  participant Kraken
  User->>Trader: Start LIVE session
  Trader->>Kraken: /private/Balance
  Kraken-->>Trader: balances
  Trader->>Kraken: /public/Ticker & /public/Depth
  Trader->>Trader: compute signals
  Trader->>Kraken: AddOrder (market)
  Kraken-->>Trader: txid
  Trader->>logs: write session JSON
```

## Notes on signals and filters
- Signals include premium gap, spread compression, momentum, and order book imbalance.
- Filters apply Kraken minimums, holdings-awareness, and configured profit/position thresholds.
- Execution only occurs when an opportunity passes all filters in live mode.
