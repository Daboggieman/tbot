import logging
import pandas as pd

class SignalScorer:
    """
    Calculates a confidence score for a trading signal based on multiple factors.
    """

    def __init__(self, weights=None):
        """
        Initializes the SignalScorer with a dictionary of weights.
        """
        if weights is None:
            self.weights = {
                'technical_signal': 0.4, # The base signal from the strategy
                'sentiment': 0.2,        # News sentiment
                'themes': 0.1,           # Number of relevant themes
                'pattern': 0.2,          # Strength of any detected candlestick pattern
                'volatility': 0.1,       # Market volatility
            }
        else:
            self.weights = weights
        
        # Define the strength of various patterns on a 0-1 scale
        self.pattern_strengths = {
            'Three White Soldiers': 1.0,
            'Three Black Crows': 1.0,
            'Bullish Engulfing': 0.9,
            'Bearish Engulfing': 0.9,
            'Morning Star': 0.8,
            'Evening Star': 0.8,
            'Hammer': 0.7,
            'Inverted Hammer': 0.7,
            'Hanging Man': 0.7,
            'Shooting Star': 0.7,
            'Tweezer Top': 0.6,
            'Tweezer Bottom': 0.6,
            'Doji': 0.4, # Doji indicates indecision, so it's a weaker confirmation
        }
        
        logging.info(f"SignalScorer initialized with weights: {self.weights}")

    def _normalize(self, value, min_val, max_val):
        """Normalizes a value to a 0-1 scale."""
        if max_val == min_val:
            return 0.5
        return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

    def calculate_score(self, context: dict) -> int:
        """
        Calculates a confidence score from 0 to 100 based on the provided context.

        Args:
            context (dict): A dictionary containing all relevant data for decision-making.

        Returns:
            int: A confidence score from 0 to 100.
        """
        signal = context.get('signal')
        if not signal or signal == 'HOLD':
            return 50 # Neutral score for a HOLD signal

        scores = {}

        # 1. Technical Signal (Base)
        scores['technical_signal'] = 1.0

        # 2. Sentiment Score
        sentiment_score = context.get('sentiment_score', 0.0)
        norm_sentiment = self._normalize(sentiment_score, -1.0, 1.0)
        scores['sentiment'] = norm_sentiment if signal == 'BUY' else 1.0 - norm_sentiment

        # 3. Thematic Matches
        thematic_matches = len(context.get('themes', []))
        scores['themes'] = self._normalize(thematic_matches, 0, 5)

        # 4. Pattern Strength
        patterns = context.get('detected_patterns', [])
        pattern_score = 0.0
        if patterns:
            for p in patterns:
                pattern_name = p.get('name')
                pattern_type = p.get('type')
                if (signal == 'BUY' and pattern_type == 'bullish') or \
                   (signal == 'SELL' and pattern_type == 'bearish') or \
                   (pattern_type == 'reversal'):
                    pattern_score = max(pattern_score, self.pattern_strengths.get(pattern_name, 0.3))
        scores['pattern'] = pattern_score

        # 5. Volatility Confirmation (Example: higher volatility is better for pattern breakouts)
        market_data = context.get('market_data')
        if market_data is not None and not market_data.empty:
            returns = market_data['close'].pct_change()
            # Normalize volatility (e.g., assuming annualized volatility range of 0% to 50%)
            volatility = returns.std() * (252**0.5)
            scores['volatility'] = self._normalize(volatility, 0, 0.5)
        else:
            scores['volatility'] = 0.5 # Neutral if no data

        # Final Weighted Calculation
        total_score = 0.0
        total_weight = 0.0
        for factor, score in scores.items():
            weight = self.weights.get(factor, 0)
            if weight > 0:
                total_score += score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 50

        final_score = (total_score / total_weight) * 100
        return int(final_score)
