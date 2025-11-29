# Architecture

This document provides a deeper look into the trading engine architecture.

## System Overview
- Kraken API client with persistent nonce
- Signal detectors: premium gap, spread compression, momentum, order book imbalance
- Execution engine honoring Kraken minimums and live balances
- Logging for sessions and PnL

## Diagrams
```mermaid
flowchart LR
  env[.env] --> api[KrakenAPI]
  api --> bal[Balance Check]
  bal --> pairs[Pair Selection]
  pairs --> strat[Strategies]
  strat --> exec[Execution]
  exec --> logs[Session Logs]
```

```mermaid
classDiagram
  class KrakenAPI {
    +get_ticker(pair)
    +get_order_book(pair, count)
    +get_balance()
    +place_order(pair, order_type, side, volume)
  }
  class TraderV2 {
    +scan_for_opportunities()
    +execute_trade(opp, paper_mode)
    +run(duration, paper_mode)
  }
  KrakenAPI <|-- TraderV2
```
