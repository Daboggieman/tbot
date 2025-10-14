# Project Overhaul Tasks (2025-10-14)

This section outlines the next set of major improvements for the bot.

---

## 1. Streamline Application Startup

**Goal:** Eliminate the need to manually start multiple scripts. A single command should launch the entire application stack (data feeds, executors, and the bot itself).

**Proposed Solution:**
- [x] Create a master startup script (`start_all.bat` for Windows) that will:
  1. Launch the `data_downloader_api.py` in the background.
  2. Launch the `mt5_bridge.py` in the background.
  3. Launch the `mt5_order_executor.py` in the background.
  4. Run `docker-compose up -d`.
- This provides a single-click startup without the complexity of networking the MT5 terminal into Docker.

**Files to Create/Edit:**
- [x] `start_all.bat` (New file)
- [x] `README.md` (To document the new startup procedure)

---

## 2. Migrate External Data to Alpha Vantage

**Goal:** Improve efficiency and consolidate APIs by migrating both historical data and news fetching to Alpha Vantage.

**Research & Decision:**
- [x] **Research:** Compare Alpha Vantage, Finage, Financial Modeling Prep, and IEX Cloud.
- [x] **Decision:** Select Alpha Vantage for its superior M1 Forex data, built-in sentiment analysis, and generous free tier.

**Implementation Steps:**
- [x] **API Client:** Create a new Python script (`bot/external_data_client.py`) to handle fetching both price and news data from the Alpha Vantage API.
- [x] **API Key Management:** Add the new `ALPHA_VANTAGE_API_KEY` to the environment/`.env` file.
- [x] **Price Integration:** Modify `historical_data_importer.py` to call the new client instead of connecting to MT5. Ensure the data is saved in the same CSV format.
- [x] **News Integration:** Modify `bot/news_fetcher.py` to call the new Alpha Vantage client, replacing the `newsapi.org` logic and local sentiment analysis.
- [ ] **Cleanup:** Deprecate the `NEWS_API_KEY` and potentially the `data_downloader_api.py` if the new process is fast enough to be synchronous.

**Files to Create/Edit:**
- `bot/external_data_client.py` (New file)
- `historical_data_importer.py` (Modify)
- `bot/news_fetcher.py` (Modify)
- `.env` / `docker-compose.yml` (Add/Remove API keys)
- `README.md` (Document the new data source)

---

## 3. Fix Post-News Quiet Period

**Goal:** The bot should resume trading more quickly after a high-impact news event. The current quiet period extends too long after the event.

**Analysis:**
- [ ] Review the `_is_in_quiet_period` method in `bot/consumer.py`.
- [ ] Analyze the logic: `(event_time - quiet_period) <= now <= (event_time + quiet_period)`.

**Proposed Solution:**
- Modify the logic to be asymmetrical. For example, have a 30-minute quiet period *before* the event and only a 5-minute quiet period *after* the event.
- This will involve changing the single `self.quiet_period` variable to two variables (e.g., `self.quiet_period_before` and `self.quiet_period_after`).

**Files to Create/Edit:**
- `bot/consumer.py` (Modify `__init__` and `_is_in_quiet_period`)
- `main.py` (Update CLI arguments if the quiet period becomes configurable with two values).

---

# TODO: Implement Automated Trade Lifecycle Management (Phase C)

## Overview

The bot needs to autonomously manage the entire lifecycle of a trade after it has been opened. This includes monitoring for Stop Loss (SL) and Take Profit (TP) hits, and applying a trailing stop to protect profits.

## Steps

- [ ] **OrderManager:** Enhance `bot/order_manager.py` to track the state of open positions. It should store the position details (symbol, volume, entry price, SL, TP, etc.) after an order is successfully placed.

- [ ] **OrderManager:** Add a `close_position` method to `bot/order_manager.py`. This method will publish a `CLOSE` order message to the `trade_orders` queue, including the position/ticket ID to be closed.

- [ ] **OrderManager:** Add a `modify_position` method to `bot/order_manager.py`. This will be used for updating the SL and TP for trailing stops.

- [ ] **Consumer:** Create a new `_manage_open_positions` method in `bot/consumer.py`. This method will iterate through the open positions being tracked by the `OrderManager`.

- [ ] **Consumer:** Inside `_manage_open_positions`, add logic to check if the current market price has crossed the SL or TP of any open position. If it has, call the `order_manager.close_position()` method.

- [ ] **Consumer:** Inside `_manage_open_positions`, add logic to implement a simple trailing stop. For example, if a BUY position is in profit by a certain amount, update the SL to lock in some of the profit by calling `order_manager.modify_position()`.

- [ ] **Consumer:** Call the new `_manage_open_positions` method at the beginning of the main `_callback` function in `bot/consumer.py` so that positions are checked on every new tick.

- [ ] **Executor:** Update `mt5_order_executor.py` to handle the new `CLOSE` and `MODIFY` order types from the queue, using the appropriate `MetaTrader5` functions to close or modify trades.

## Files to Edit

- `bot/order_manager.py`
- `bot/consumer.py`
- `mt5_order_executor.py`

## Testing Strategy

1. After implementation, we will start the bot and manually place a trade.
2. We will monitor the logs to ensure the `OrderManager` tracks the position.
3. We will wait for the price to move and verify that the trailing stop logic correctly triggers a `MODIFY` order in the logs.
4. We will let the price hit the new SL or the original TP and verify that a `CLOSE` order is triggered and executed.