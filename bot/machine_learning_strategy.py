import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, classification_report
import joblib
import os

class MachineLearningStrategy:
    """
    A strategy that uses a machine learning model to generate trading signals.
    """
    def __init__(self, model_path="ml_model.pkl", rsi_window=14, macd_fast=12, macd_slow=26, macd_signal=9):
        self.model = None
        self.model_path = model_path
        self.rsi_window = rsi_window
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal

        if os.path.exists(self.model_path):
            self.load_model()

    def _calculate_rsi(self, data, window):
        """Calculates the Relative Strength Index (RSI)."""
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def _calculate_macd(self, data, fast, slow, signal):
        """Calculates the Moving Average Convergence Divergence (MACD)."""
        exp1 = data['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = data['Close'].ewm(span=slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd, signal_line

    def prepare_data(self, data):
        """
        Prepares the data for training a machine learning model.

        Args:
            data (pd.DataFrame): The historical market data.

        Returns:
            tuple: A tuple containing the features (X) and labels (y).
        """
        # Create features
        data['returns'] = data['Close'].pct_change()
        data['sma_5'] = data['Close'].rolling(window=5).mean()
        data['sma_10'] = data['Close'].rolling(window=10).mean()
        data['rsi'] = self._calculate_rsi(data, self.rsi_window)
        data['macd'], data['macd_signal'] = self._calculate_macd(data, self.macd_fast, self.macd_slow, self.macd_signal)

        data.dropna(inplace=True)

        # Create labels
        data['signal'] = 0
        data.loc[data['returns'] > 0, 'signal'] = 1
        data.loc[data['returns'] < 0, 'signal'] = -1

        feature_names = ['sma_5', 'sma_10', 'rsi', 'macd', 'macd_signal']
        X = data[feature_names]
        y = data['signal']

        return X, y

    def train_model(self, X, y):
        """
        Trains a machine learning model.

        Args:
            X (pd.DataFrame): The features.
            y (pd.Series): The labels.
        """
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        self.save_model()

        # Evaluate the model
        y_pred = self.model.predict(X_test)
        print(f"Model F1-score: {f1_score(y_test, y_pred, average='weighted')}")
        print("\nClassification Report:")
        print(classification_report(y_test, y_pred))

    def generate_signals(self, data):
        """
        Generates trading signals for the given data using the trained model.

        Args:
            data (pd.DataFrame): The historical market data.

        Returns:
            pd.DataFrame: The data with a 'signal' column.
        """
        if self.model is None:
            raise Exception("Model has not been trained or loaded yet.")

        # Create features
        data['sma_5'] = data['Close'].rolling(window=5).mean()
        data['sma_10'] = data['Close'].rolling(window=10).mean()
        data['rsi'] = self._calculate_rsi(data, self.rsi_window)
        data['macd'], data['macd_signal'] = self._calculate_macd(data, self.macd_fast, self.macd_slow, self.macd_signal)
        
        data.dropna(inplace=True)

        feature_names = ['sma_5', 'sma_10', 'rsi', 'macd', 'macd_signal']
        X = data[feature_names]

        signals = pd.DataFrame(index=X.index)
        signals['signal'] = self.model.predict(X)
        # The signal is the position, no need to calculate positions separately
        signals['positions'] = signals['signal'].diff()

        return signals

    def save_model(self):
        """Saves the trained model to a file."""
        if self.model:
            joblib.dump(self.model, self.model_path)
            print(f"Model saved to {self.model_path}")

    def load_model(self):
        """Loads a pre-trained model from a file."""
        try:
            self.model = joblib.load(self.model_path)
            print(f"Model loaded from {self.model_path}")
        except FileNotFoundError:
            print(f"No model found at {self.model_path}")
            self.model = None
