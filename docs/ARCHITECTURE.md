# Architecture

This document provides a deeper look into the trading engine architecture.

## Table of Contents
- System Overview
- Diagrams
- Components
- Data Flow
- Runtime Behavior

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

## Components
- `KrakenAPI`: thin client for private/public endpoints, with nonce management
- `TraderV2`: orchestrates scanning, filtering, and execution
- `agents/`: modular strategies, risk guards, and supervisors
- `config/`: declarative behavior for bots/regimes

## Data Flow
1. Load `.env` → API keys, pairs, thresholds
2. Verify balances (`/private/Balance`) → account banner
3. Fetch market data (`/public/Ticker`, `/public/Depth`)
4. Compute signals → assemble opportunities
5. Risk filters + minimums → executable set
6. Place order (live) or log (paper) → write session

## Runtime Behavior
- Paper mode: scans continuously, logs opportunities and simulated outcomes
- Live mode: executes orders that pass filters, writes trade log and session PnL
