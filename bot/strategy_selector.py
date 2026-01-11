import logging
import pandas as pd
from typing import Dict, Any

# Import all available strategy classes
from realtime_strategies import (
    RealtimeSentimentAwareMovingAverageCrossoverStrategy,
    RealtimeIntermarketAwareMovingAverageCrossoverStrategy,
    RealtimeThematicStrategy,
    RealtimePatternBasedStrategy,
    RealtimeMovingAverageCrossoverStrategy,
    RealtimeStandardStrategy
)
import strategies
from optimization_config import BEST_PARAMS, DISABLED_STRATEGIES

class StrategySelector:
    def __init__(self, market_context_analyzer: Any, thematic_analyzer: Any, capital_allocator: Any):
        self.market_context_analyzer = market_context_analyzer
        self.thematic_analyzer = thematic_analyzer
        self.capital_allocator = capital_allocator
        
        # Dynamic discovery of all modular strategies
        self.modular_strategies = {
            name.lower().replace('strategy', ''): cls 
            for name, cls in vars(strategies).items() 
            if isinstance(cls, type) and name.endswith('Strategy')
        }
        
        # Hardcoded overrides for legacy/specific realtime implementations
        self.realtime_overrides = {
            "sentiment": RealtimeSentimentAwareMovingAverageCrossoverStrategy,
            "intermarket": RealtimeIntermarketAwareMovingAverageCrossoverStrategy,
            "thematic": RealtimeThematicStrategy,
            "pattern": RealtimePatternBasedStrategy,
            "simple_ma": RealtimeMovingAverageCrossoverStrategy,
        }
        # Mapping from strategy selector keys to BEST_PARAMS keys
        self.param_mapping = {
            "sentiment": "moving_average_crossover",  # Assuming sentiment uses MA params
            "intermarket": "moving_average_crossover",
            "thematic": None,  # Thematic doesn't use BEST_PARAMS
            "pattern": None,
            "simple_ma": "moving_average_crossover",
        }

        # Regime-specific parameter adjustments
        self.regime_adjustments = {
            "moving_average_crossover": {
                "Trending": {"short_window": 0.8, "long_window": 0.8},  # Shorter windows for quicker signals
                "Ranging": {"short_window": 1.2, "long_window": 1.2},   # Longer windows for smoother signals
                "Volatile": {"short_window": 1.0, "long_window": 1.0},  # Default
                "Unknown": {"short_window": 1.0, "long_window": 1.0}
            },
            "rsi": {
                "Trending": {"window": 0.8, "buy_threshold": 1.1, "sell_threshold": 0.9},  # Shorter window, tighter thresholds
                "Ranging": {"window": 1.2, "buy_threshold": 0.9, "sell_threshold": 1.1},   # Longer window, wider thresholds
                "Volatile": {"window": 1.0, "buy_threshold": 1.0, "sell_threshold": 1.0},
                "Unknown": {"window": 1.0, "buy_threshold": 1.0, "sell_threshold": 1.0}
            },
            # Add for other strategies as needed
        }

        print("StrategySelector initialized.")

    def _adjust_params_for_regime(self, strategy_name, params, regime):
        """
        Adjusts strategy parameters based on the detected market regime.

        Args:
            strategy_name (str): The name of the strategy.
            params (dict): The original parameters.
            regime (str): The detected market regime.

        Returns:
            dict: The adjusted parameters.
        """
        if strategy_name not in self.regime_adjustments or regime not in self.regime_adjustments[strategy_name]:
            return params

        adjustments = self.regime_adjustments[strategy_name][regime]
        adjusted_params = params.copy()

        for key, multiplier in adjustments.items():
            if key in adjusted_params:
                adjusted_params[key] = int(adjusted_params[key] * multiplier)

        return adjusted_params

    def select_strategy(self, context: dict) -> Any:
        """
        Analyzes market data and selects the best strategy to execute.

        Args:
            context (dict): A dictionary containing all relevant data for decision-making.

        Returns:
            An instantiated strategy object ready to be executed, or None if no strategy is suitable.
        """
        print("Selecting strategy...")
        
        # Extract data from context
        symbol = context.get('symbol')
        market_data = context.get('market_data')
        news_sentiment = context.get('sentiment_score', 0.0)
        detected_patterns = context.get('detected_patterns', [])
        themes = context.get('themes', [])

        if market_data is None or market_data.empty or len(market_data) < 2:
            print("Not enough market data to select a strategy.")
            return None

        # Step 1: Detect Market Regime
        regime = self.market_context_analyzer.detect_market_regime(symbol) if self.market_context_analyzer else 'Unknown'
        print(f"Detected Market Regime: {regime}")
        print(f"Applying regime-aware parameter adjustments for regime: {regime}")

        # Step 2: Analyze other factors
        has_strong_sentiment = abs(news_sentiment) > 0.5
        has_engulfing_pattern = any(p['name'] == 'Engulfing' for p in detected_patterns)
        has_inflation_theme = 'inflation' in themes

        # Step 3: Decision Logic
        logging.info(f"Decision Factors: Strong Sentiment: {has_strong_sentiment}, Engulfing Pattern: {has_engulfing_pattern}, Inflation Theme: {has_inflation_theme}")

        # Check for hardcoded strategies first (legacy compatibility)
        for key, strategy_cls in self.realtime_overrides.items():
            if key in DISABLED_STRATEGIES:
                continue
            
            allocation = self.capital_allocator.get_allocation(key)
            if allocation <= 0:
                continue
                
            # Legacy logic for hardcoded strategies
            if key == "thematic" and has_inflation_theme and has_strong_sentiment:
                return strategy_cls(symbol=symbol, data=market_data, required_themes=['inflation'])
            elif key == "pattern" and has_engulfing_pattern and regime == 'Volatile':
                return strategy_cls(symbol=symbol, data=market_data, patterns_to_use=['Engulfing'])
            elif key == "sentiment" and has_strong_sentiment:
                params = self._get_adjusted_params("moving_average_crossover", regime)
                return strategy_cls(symbol=symbol, data=market_data, sentiment_threshold=0.5, **params)
            elif key == "simple_ma" and regime == 'Ranging':
                params = self._get_adjusted_params("moving_average_crossover", regime)
                return strategy_cls(symbol=symbol, data=market_data, **params)
            elif key == "intermarket":
                params = self._get_adjusted_params("moving_average_crossover", regime)
                return strategy_cls(symbol=symbol, data=market_data, market_context_analyzer=self.market_context_analyzer, correlation_symbol='SPY', **params)

        # Dynamic selection for all other modular strategies
        for name, strategy_cls in self.modular_strategies.items():
            if name in DISABLED_STRATEGIES:
                continue
            
            allocation = self.capital_allocator.get_allocation(name)
            if allocation <= 0:
                continue

            # Basic logic: match strategy to regime
            # (In a real system, this would be more complex/configurable)
            params = self._get_adjusted_params(name, regime)
            
            logging.info(f"Dynamically selecting {name} strategy for regime {regime}")
            return RealtimeStandardStrategy(
                symbol=symbol,
                data=market_data,
                strategy_class=strategy_cls,
                **params
            )

        logging.info("All strategies are disabled or no suitable strategy found.")
        return None

    def _get_adjusted_params(self, name: str, regime: str) -> dict:
        """Helper to get and adjust parameters for a strategy."""
        param_key = self.param_mapping.get(name, name)
        params = BEST_PARAMS.get(param_key, {})
        return self._adjust_params_for_regime(param_key, params, regime)
