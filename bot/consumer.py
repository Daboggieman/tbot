import pika
import time
import logging
import json
import threading
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone

from order_manager import OrderManager
from news_fetcher import NewsFetcher
from economic_calendar import get_economic_events
from retry_utils import retry_with_backoff
from market_context_analyzer import MarketContextAnalyzer
from realtime_candle_pattern_detector import RealtimeCandlePatternDetector
from signal_scorer import SignalScorer
from thematic_analyzer import ThematicAnalyzer
from strategy_selector import StrategySelector
from historical_data_manager import HistoricalDataManager
from technical_indicators import calculate_atr
from telegram_notifier import TelegramNotifier
from config import get_config


class Consumer:
    def __init__(self, symbol, broker, capital_allocator, order_manager=None, news_fetcher=None, scorer=None, notifier=None, secondary_symbol=None, correlation_window_minutes=60, quiet_period_before_minutes=30, quiet_period_after_minutes=5, candle_interval_minutes=1, default_volume=0.1, default_sl_points=50, default_tp_points=100, default_slippage=5, trailing_stop_pips=20, risk_per_trade_percent=1.0, atr_multiplier=1.5):
        cfg = get_config()
        self.host = cfg.BROKER_HOST
        self.port = cfg.BROKER_PORT
        self.username = cfg.BROKER_USER
        self.password = cfg.BROKER_PASS
        self.symbol = symbol
        self.broker = broker
        self.capital_allocator = capital_allocator
        self.secondary_symbol = secondary_symbol
        self.default_volume = default_volume
        self.default_sl_points = default_sl_points
        self.default_tp_points = default_tp_points
        self.default_slippage = default_slippage
        self.trailing_stop_pips = trailing_stop_pips
        self.risk_per_trade_percent = risk_per_trade_percent
        self.atr_multiplier = atr_multiplier
        self.pip_size = 0.0001 # Assuming forex pip size
        self.confidence_threshold = 40 
        self.candle_interval = timedelta(minutes=candle_interval_minutes)
        self.candle_interval_minutes = candle_interval_minutes
        
        self._credentials = pika.PlainCredentials(self.username, self.password)
        self._parameters = pika.ConnectionParameters(
            host=self.host, 
            port=self.port, 
            virtual_host='/', 
            credentials=self._credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )

        # --- Account State ---
        # Initial default values, updated by live data from the executor.
        self.account_balance = 10000.0
        self.account_equity = 10000.0
        self.last_account_info_request = time.time()
        # ---------------------

        self.connection = None
        self.channel = None
        self.order_manager = order_manager if order_manager else OrderManager(self.broker, self.capital_allocator)
        self.news_fetcher = news_fetcher if news_fetcher else NewsFetcher()
        self.scorer = scorer if scorer else SignalScorer()
        self.notifier = notifier if notifier else TelegramNotifier()
        
        self.sentiment_score = 0.0
        self.themes = []
        self.last_news_fetch_time = None
        self.news_fetch_interval = timedelta(minutes=15)
        
        self.quiet_period_before = timedelta(minutes=quiet_period_before_minutes)
        self.quiet_period_after = timedelta(minutes=quiet_period_after_minutes)
        self.high_impact_events = []

        self.current_candle = None
        self.last_candle_time = None

        self.pattern_detector = RealtimeCandlePatternDetector(pattern_window=50) # Window must be >= longest MA
        self.detected_patterns = []
        
        self.market_analyzer = None
        if self.secondary_symbol:
            logging.info(f"Initializing MarketContextAnalyzer for {self.symbol} and {self.secondary_symbol}")
            self.market_analyzer = MarketContextAnalyzer(
                symbols_to_monitor=[self.symbol, self.secondary_symbol],
                correlation_window_minutes=correlation_window_minutes,
                primary_symbol=self.symbol
            )
        
        self.thematic_analyzer = ThematicAnalyzer()
        self.strategy_selector = StrategySelector(
            market_context_analyzer=self.market_analyzer,
            thematic_analyzer=self.thematic_analyzer,
            capital_allocator=self.capital_allocator
        )

        # Prime the data buffer with historical data to avoid a cold start
        self._prime_data_buffer()

        # Load economic events in a background thread to avoid blocking startup
        events_thread = threading.Thread(target=self._load_economic_events, daemon=True)
        events_thread.start()

        # Request account info on startup
        self.order_manager.request_account_info()
        self.notifier.send_message(f"**Consumer Initialized**\nSymbol: {self.symbol}\nMode: {self.broker.mode}")


    def _get_timeframe_string(self):
        timeframe_map = {1: 'M1', 5: 'M5', 15: 'M15', 60: 'H1', 1440: 'D1'}
        timeframe_str = timeframe_map.get(self.candle_interval_minutes)
        if not timeframe_str:
            logging.warning(f"No standard timeframe string found for interval {self.candle_interval_minutes}m. Cannot prime data.")
        return timeframe_str

    def _request_data_download(self, timeframe_str):
        api_url = "http://host.docker.internal:9091/download"
        logging.info(f"Requesting data download from {api_url} for {self.symbol} {timeframe_str}...")
        try:
            payload = {'symbol': self.symbol, 'timeframe': timeframe_str}
            response = requests.post(api_url, json=payload, timeout=120) 
            if response.status_code in [200, 202]:
                logging.info("Data download request successful. Will attempt to reload.")
                time.sleep(5) 
                return True
            else:
                logging.error(f"API request to download data failed with status {response.status_code}: {response.text}")
                return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Could not connect to data downloader API at {api_url}. Please ensure it is running on the host machine. Error: {e}")
            return False

    def _fill_buffer_from_df(self, hist_data):
        num_to_prime = self.pattern_detector.data.maxlen
        priming_data = hist_data.tail(num_to_prime)
        logging.info(f"Found {len(priming_data)} records for priming.")
        for index, row in priming_data.iterrows():
            candle = {
                'Timestamp': index.to_pydatetime().replace(tzinfo=timezone.utc),
                'Open': row['Open'],
                'High': row['High'],
                'Low': row['Low'],
                'Close': row['Close']
            }
            self.pattern_detector.add_candle(candle)
        logging.info(f"Successfully primed data buffer with {len(self.pattern_detector.data)} historical candles.")

    def _prime_data_buffer(self):
        logging.info("Attempting to prime data buffer with historical data...")
        hdm = HistoricalDataManager()
        timeframe_str = self._get_timeframe_string()
        if not timeframe_str: return

        hist_data = hdm.load_data_from_csv(self.symbol, timeframe_str)

        # Check if data is insufficient (None or less than 50 records)
        if hist_data is None or len(hist_data) < 50:
            if hist_data is None:
                logging.warning(f"Historical data file for {self.symbol}_{timeframe_str} not found.")
            else:
                logging.warning(f"Insufficient historical data found for {self.symbol}_{timeframe_str} ({len(hist_data)} records). Need at least 50.")
            
            if self._request_data_download(timeframe_str):
                # Poll for the file to appear
                max_retries = 24 # 24 * 5 seconds = 120 seconds
                for i in range(max_retries):
                    logging.info(f"Polling for historical data file... (Attempt {i+1}/{max_retries})")
                    hist_data = hdm.load_data_from_csv(self.symbol, timeframe_str)
                    if hist_data is not None and len(hist_data) >= 50:
                        logging.info("Historical data file found and is sufficient.")
                        break
                    time.sleep(5)
                else: # This else belongs to the for loop, executes if loop finishes without break
                    logging.error("Failed to load historical data after multiple attempts.")


        if hist_data is not None and not hist_data.empty:
            self._fill_buffer_from_df(hist_data)
        else:
            logging.warning("Could not load historical data for priming. The bot will start with an empty data buffer.")

    @retry_with_backoff(allowed_exceptions=(pika.exceptions.AMQPConnectionError,))
    def connect(self):
        """Establishes a connection and channel to RabbitMQ."""
        if self.connection and self.connection.is_open:
            return

        logging.info("Attempting to connect to RabbitMQ...")
        credentials = pika.PlainCredentials(self.username, self.password)
        parameters = pika.ConnectionParameters(self.host, self.port, '/', credentials, heartbeat=600)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        logging.info("Consumer connected to RabbitMQ successfully.")
        self.notifier.send_message("Consumer connected to RabbitMQ successfully.")

    def _load_economic_events(self):
        """Fetches and stores high-impact economic events for the next 7 days."""
        logging.info("Loading economic events for the upcoming week...")
        try:
            events_df = get_economic_events(days_ahead=7)
            if not events_df.empty:
                high_impact_df = events_df[events_df['importance'] == 'high'].copy()
                high_impact_df['datetime'] = high_impact_df.apply(
                    lambda row: datetime.strptime(f"{row['date']} {row['time']}", '%d/%m/%Y %H:%M:%S'), axis=1
                )
                self.high_impact_events = [
                    pd.Timestamp(dt).tz_localize('UTC') for dt in high_impact_df['datetime']
                ]
                logging.info(f"Successfully loaded {len(self.high_impact_events)} high-impact economic events.")
            else:
                logging.warning("Could not fetch economic events or none were found.")
        except Exception as e:
            logging.error(f"An error occurred while loading economic events: {e}")

    def _is_in_quiet_period(self):
        """Checks if the current time is within an asymmetrical quiet period around a high-impact event."""
        now_utc = datetime.now(timezone.utc)
        for event_time in self.high_impact_events:
            if (event_time - self.quiet_period_before) <= now_utc <= (event_time + self.quiet_period_after):
                logging.warning(f"Trading paused. In quiet period for high-impact event at {event_time}.")
                self.notifier.send_message(f"⚠️ Trading paused. In quiet period for high-impact event at {event_time}.")
                return True
        return False

    def _manage_open_positions(self, current_price):
        """
        Checks all open positions for SL/TP hits or trailing stop updates.
        """
        open_positions = self.order_manager.get_open_positions()
        if not open_positions:
            return

        logging.debug(f"Managing {len(open_positions)} open position(s).")

        for pid, pos in open_positions.items():
            order_type = pos['order_type']
            entry_price = pos['entry_price']
            sl = pos['stop_loss']
            tp = pos['take_profit']

            # Check for SL/TP hit
            if order_type == 'BUY':
                if current_price <= sl:
                    logging.info(f"Stop loss hit for BUY position {pid} at price {current_price}.")
                    self.notifier.send_message(f"🔴 SL Hit for BUY position {pid} at {current_price}.")
                    self.order_manager.close_position(pid, current_price)
                    continue # Move to next position
                if current_price >= tp:
                    logging.info(f"Take profit hit for BUY position {pid} at price {current_price}.")
                    self.notifier.send_message(f"🟢 TP Hit for BUY position {pid} at {current_price}.")
                    self.order_manager.close_position(pid, current_price)
                    continue
            elif order_type == 'SELL':
                if current_price >= sl:
                    logging.info(f"Stop loss hit for SELL position {pid} at price {current_price}.")
                    self.notifier.send_message(f"🔴 SL Hit for SELL position {pid} at {current_price}.")
                    self.order_manager.close_position(pid, current_price)
                    continue
                if current_price <= tp:
                    logging.info(f"Take profit hit for SELL position {pid} at price {current_price}.")
                    self.notifier.send_message(f"🟢 TP Hit for SELL position {pid} at {current_price}.")
                    self.order_manager.close_position(pid, current_price)
                    continue

            # Trailing Stop Logic
            trailing_stop_distance = self.trailing_stop_pips * self.pip_size
            if order_type == 'BUY':
                # If price moves in our favor, trail the stop loss
                if current_price > entry_price + trailing_stop_distance:
                    new_sl = current_price - trailing_stop_distance
                    # We only move the stop loss up, never down
                    if new_sl > sl:
                        logging.info(f"Trailing stop for BUY position {pid}. New SL: {new_sl}")
                        self.notifier.send_message(f"📈 Trailing SL for BUY {pid}. New SL: {new_sl}")
                        self.order_manager.modify_position(pid, new_stop_loss=new_sl)
            elif order_type == 'SELL':
                # If price moves in our favor, trail the stop loss
                if current_price < entry_price - trailing_stop_distance:
                    new_sl = current_price + trailing_stop_distance
                    # We only move the stop loss down, never up
                    if new_sl < sl:
                        logging.info(f"Trailing stop for SELL position {pid}. New SL: {new_sl}")
                        self.notifier.send_message(f"📉 Trailing SL for SELL {pid}. New SL: {new_sl}")
                        self.order_manager.modify_position(pid, new_stop_loss=new_sl)

    def _update_news_data(self):
        """Fetches recent news and updates sentiment score and themes."""
        now = datetime.utcnow()
        if self.last_news_fetch_time is None or (now - self.last_news_fetch_time) > self.news_fetch_interval:
            logging.info("Fetching news for analysis...")
            start_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
            news_df = self.news_fetcher.fetch_news_and_analyze_sentiment(self.symbol, start_date, end_date)
            
            if not news_df.empty:
                self.sentiment_score = news_df['sentiment'].mean()
                logging.info(f"Updated sentiment score for {self.symbol}: {self.sentiment_score}")
                
                all_themes = [theme for sublist in news_df['themes'].dropna() for theme in sublist]
                self.themes = list(set(all_themes))
                logging.info(f"Updated themes for {self.symbol}: {self.themes}")
            else:
                logging.info("No new news found. Sentiment and themes remain unchanged.")
            self.last_news_fetch_time = now

    def _aggregate_tick(self, tick_data):
        price = tick_data.get('ask')
        if price is None: return
        tick_time = datetime.fromtimestamp(tick_data.get('timestamp_msc') / 1000, tz=timezone.utc)
        if self.last_candle_time is None:
            if len(self.pattern_detector.data) > 0:
                self.last_candle_time = list(self.pattern_detector.data)[-1]['Timestamp']
            else:
                self.last_candle_time = tick_time.replace(second=0, microsecond=0)
        if tick_time - self.last_candle_time >= self.candle_interval:
            if self.current_candle:
                logging.info(f"New {self.candle_interval.seconds // 60}m candle closed for {self.symbol}: O={self.current_candle['Open']}, H={self.current_candle['High']}, L={self.current_candle['Low']}, C={self.current_candle['Close']}")
                self.pattern_detector.add_candle(self.current_candle)
                self.detected_patterns = self.pattern_detector.detect_at_latest_candle()
                if self.detected_patterns:
                    logging.info(f"Detected patterns: {self.detected_patterns}")
            self.last_candle_time += self.candle_interval
            self.current_candle = {'Timestamp': self.last_candle_time, 'Open': price, 'High': price, 'Low': price, 'Close': price}
        else:
            if self.current_candle:
                self.current_candle['High'] = max(self.current_candle['High'], price)
                self.current_candle['Low'] = min(self.current_candle['Low'], price)
                self.current_candle['Close'] = price
            elif not self.current_candle and len(self.pattern_detector.data) == 0:
                 self.current_candle = {'Timestamp': self.last_candle_time, 'Open': price, 'High': price, 'Low': price, 'Close': price}

    def _process_signals(self, tick_data, price, method):
        """Processes signals and executes trades if necessary."""
        self._update_news_data()

        market_data_df = pd.DataFrame(list(self.pattern_detector.data))
        if market_data_df.empty:
            return

        market_data_df = market_data_df.rename(columns={
            'Timestamp': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close'
        })

        context = {
            'symbol': self.symbol,
            'tick_data': tick_data,
            'market_data': market_data_df,
            'sentiment_score': self.sentiment_score,
            'themes': self.themes,
            'detected_patterns': self.detected_patterns,
            'market_analyzer': self.market_analyzer
        }

        selected_strategy = self.strategy_selector.select_strategy(context)
        if not selected_strategy:
            logging.info("No suitable strategy selected.")
            return

        strategy_name = type(selected_strategy).__name__
        signal = selected_strategy.generate_signal(context)
        
        if signal == 'HOLD':
            return

        logging.info(f"Strategy {strategy_name} generated signal: {signal}")
        context['signal'] = signal
        confidence_score = self.scorer.calculate_score(context)
        logging.info(f"Signal Confidence Score: {confidence_score}/100")

        if confidence_score > self.confidence_threshold:
            self.notifier.send_message(f"💡 **Signal Alert** ({self.symbol})\nSignal: {signal}\nStrategy: {strategy_name}\nConfidence: {confidence_score:.2f}/100")
            
            current_atr = calculate_atr(market_data_df.rename(columns={'timestamp': 'Timestamp', 'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close'}))
            if current_atr <= 0:
                logging.warning("ATR is not positive. Cannot calculate position size.")
                return

            strategy_allocation_percent = self.capital_allocator.get_allocation(strategy_name)
            if strategy_allocation_percent <= 0:
                logging.warning(f"No capital allocated to {strategy_name}.")
                return

            effective_account_balance = self.account_equity * strategy_allocation_percent
            volume = self.order_manager.calculate_dynamic_position_size(
                symbol=self.symbol,
                account_balance=effective_account_balance,
                risk_per_trade_percent=self.risk_per_trade_percent,
                atr_value=current_atr,
                atr_multiplier=self.atr_multiplier
            )

            if volume is None or volume <= 0:
                logging.warning("Calculated volume is invalid.")
                return

            logging.info(f"Placing {signal} order: {volume} lots.")
            points_sl = self.default_sl_points
            points_tp = self.default_tp_points
            slippage = self.default_slippage

            if signal == 'BUY':
                stop_loss = price - (points_sl * self.pip_size)
                take_profit = price + (points_tp * self.pip_size)
                self.order_manager.place_market_order(self.symbol, 'BUY', volume, price, stop_loss, take_profit, slippage)
            elif signal == 'SELL':
                stop_loss = price + (points_sl * self.pip_size)
                take_profit = price - (points_tp * self.pip_size)
                self.order_manager.place_market_order(self.symbol, 'SELL', volume, price, stop_loss, take_profit, slippage)
            
            # Reset patterns after trade
            self.detected_patterns = []

    def _callback(self, ch, method, properties, body):
        try:
            data = json.loads(body.decode())
            msg_type = data.get('type')

            if msg_type == 'account_info':
                self.account_balance = data.get('balance', self.account_balance)
                self.account_equity = data.get('equity', self.account_equity)
                logging.info(f"Account update: Balance=${self.account_balance:,.2f}, Equity=${self.account_equity:,.2f}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            tick_data = data
            current_time = time.time()
            if current_time - self.last_account_info_request > 60:
                self.order_manager.request_account_info()
                self.last_account_info_request = current_time

            if self._is_in_quiet_period():
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            if self.market_analyzer:
                self.market_analyzer.handle_tick(tick_data)

            if tick_data.get('symbol') != self.symbol:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            
            self._aggregate_tick(tick_data)
            price = tick_data.get('ask')
            if price is None:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            self._manage_open_positions(price)
            
            # Decouple heavy signal processing from tick handling
            # In a true high-freq system, this might go to a worker thread pool
            self._process_signals(tick_data, price, method)

        except Exception as e:
            logging.error(f"Error in Consumer callback: {e}", exc_info=True)
            self.notifier.send_message(f"🔥 Consumer Error: {e}")
        
        ch.basic_ack(delivery_tag=method.delivery_tag)



    @retry_with_backoff(retries=10, initial_delay=2, backoff_factor=2, allowed_exceptions=(pika.exceptions.AMQPConnectionError,))
    def connect(self):
        """Connects to RabbitMQ with retry and backoff."""
        if self.connection and not self.connection.is_closed:
            return

        logging.info(f"Connecting to RabbitMQ at {self.host}:{self.port}...")
        self.connection = pika.BlockingConnection(self._parameters)
        self.channel = self.connection.channel()
        logging.info("Consumer connected to RabbitMQ.")

    def start_consuming(self, queue_name):
        """Starts consuming messages from the queue in a resilient loop."""
        while True:
            try:
                self.connect()
                # Ensure channel is open
                if not self.channel or self.channel.is_closed:
                    self.channel = self.connection.channel()
                
                self.channel.queue_declare(queue=queue_name, durable=True)
                self.channel.basic_qos(prefetch_count=1)
                self.channel.basic_consume(queue=queue_name, on_message_callback=self._callback)
                
                logging.info(f' [*] Waiting for messages on queue {queue_name}. To exit press CTRL+C')
                self.channel.start_consuming()
            except (pika.exceptions.AMQPError, ConnectionError) as e:
                logging.warning(f"RabbitMQ connection lost: {e}. Reconnecting in 5 seconds...")
                self.notifier.send_message(f"🔌 RabbitMQ connection lost: {e}. Reconnecting...")
                if self.connection and not self.connection.is_closed:
                    try:
                        self.connection.close()
                    except:
                        pass
                time.sleep(5)
            except Exception as e:
                logging.error(f"An unexpected error occurred in start_consuming: {e}. Retrying in 10 seconds...", exc_info=True)
                self.notifier.send_message(f"🔥 CRITICAL: Unexpected error in Consumer: {e}")
                time.sleep(10)
