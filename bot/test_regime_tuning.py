#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import pandas as pd
from strategy_selector import StrategySelector
from market_context_analyzer import MarketContextAnalyzer

# Create mock data
data = pd.DataFrame({
    'timestamp': pd.date_range('2023-01-01', periods=100, freq='1min'),
    'open': [1.0] * 100,
    'high': [1.01] * 100,
    'low': [0.99] * 100,
    'close': [1.0] * 100,
    'volume': [100] * 100
})

# Create analyzer
analyzer = MarketContextAnalyzer(['EURUSD'], 50, 'EURUSD')

# Add data to analyzer
for i in range(50):
    tick = {'symbol': 'EURUSD', 'ask': 1.0 + i * 0.001, 'timestamp_msc': int(data.iloc[i]['timestamp'].timestamp() * 1000)}
    analyzer.handle_tick(tick)

# Create selector
selector = StrategySelector(analyzer, None)

# Create context
context = {
    'symbol': 'EURUSD',
    'market_data': data,
    'sentiment_score': 0.0,
    'detected_patterns': [],
    'themes': []
}

# Test selection
strategy = selector.select_strategy(context)

if strategy:
    print(f"Selected strategy: {type(strategy).__name__}")
    print(f"Strategy params: {getattr(strategy, 'short_window', 'N/A')}, {getattr(strategy, 'long_window', 'N/A')}")
else:
    print("No strategy selected")
