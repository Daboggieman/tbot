class EventDrivenStrategy:
    """
    A strategy that generates signals based on real-time market events.
    """
    def __init__(self, news_sentiment_threshold=0.5, holding_period=5):
        self.news_sentiment_threshold = news_sentiment_threshold
        self.holding_period = holding_period
        self.position = 0  # -1 for short, 0 for flat, 1 for long
        self.entry_bar = -1

    def generate_signal(self, event, current_bar=None):
        """
        Generates a trading signal for a single market event.

        Args:
            event (dict): A dictionary representing a single market event.
            current_bar (int): The index of the current bar.

        Returns:
            dict: A dictionary representing a trading signal.
        """
        signal = {'signal': 'HOLD', 'symbol': event.get('symbol')}

        # If we are in a position, check if we should exit
        if self.position != 0 and current_bar is not None:
            if current_bar - self.entry_bar >= self.holding_period:
                signal['signal'] = 'SELL' if self.position == 1 else 'BUY'
                self.position = 0
                self.entry_bar = -1
                return signal

        # If we are flat, check for an entry signal
        if self.position == 0 and event.get('type') == 'news' and 'sentiment' in event:
            if event['sentiment'] > self.news_sentiment_threshold:
                signal['signal'] = 'BUY'
                self.position = 1
                self.entry_bar = current_bar
            elif event['sentiment'] < -self.news_sentiment_threshold:
                signal['signal'] = 'SELL'
                self.position = -1
                self.entry_bar = current_bar

        return signal
