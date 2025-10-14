from strategies import (
    MovingAverageCrossoverStrategy,
    RSIStrategy,
    MACDStrategy,
    BollingerBandsMeanReversionStrategy,
    BollingerBandsSqueezeStrategy
)

STRATEGY_MAP = {
    "moving_average_crossover": MovingAverageCrossoverStrategy,
    "rsi": RSIStrategy,
    "macd": MACDStrategy,
    "bollinger_bands_mean_reversion": BollingerBandsMeanReversionStrategy,
    "bollinger_bands_squeeze": BollingerBandsSqueezeStrategy
}

PARAM_GRIDS = {
    "moving_average_crossover": {
        'short_window': [10, 20, 30],
        'long_window': [40, 50, 60]
    },
    "rsi": {
        'window': [7, 14, 21],
        'buy_threshold': [25, 30, 35],
        'sell_threshold': [65, 70, 75]
    },
    "macd": {
        'fast_window': [10, 12, 15],
        'slow_window': [24, 26, 30],
        'signal_window': [7, 9, 11]
    },
    "bollinger_bands_mean_reversion": {
        'window': [15, 20, 25],
        'num_std_dev': [1.5, 2.0, 2.5]
    },
    "bollinger_bands_squeeze": {
        'window': [15, 20, 25],
        'num_std_dev': [1.5, 2.0, 2.5],
        'squeeze_threshold': [1.0, 1.5, 2.0]
    }
}



# Best parameters found from optimization, updated by walk-forward optimization
BEST_PARAMS = {'moving_average_crossover': {'short_window': 10, 'long_window': 40}, 'rsi': {'window': 14, 'buy_threshold': 30, 'sell_threshold': 70}, 'macd': {'fast_window': 12, 'slow_window': 26, 'signal_window': 9}, 'bollinger_bands_mean_reversion': {'window': 20, 'num_std_dev': 2.0}, 'bollinger_bands_squeeze': {'window': 20, 'num_std_dev': 2.0, 'squeeze_threshold': 1.5}}

# Disabled strategies based on performance review
DISABLED_STRATEGIES = {'sentiment'}
