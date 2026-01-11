import pandas as pd
import matplotlib.pyplot as plt
import logging

class Visualizer:
    """
    Visualizer for plotting backtest results.
    """
    def __init__(self, portfolio_history_file="portfolio_history.csv"):
        """
        Initializes the Visualizer.

        Args:
            portfolio_history_file (str): The path to the portfolio history CSV file.
        """
        self.portfolio_history_file = portfolio_history_file
        self.portfolio_history = None
        logging.info("Visualizer initialized.")

    def load_data(self):
        """Loads the portfolio history data from the CSV file."""
        try:
            self.portfolio_history = pd.read_csv(self.portfolio_history_file, index_col=0, parse_dates=True)
            logging.info(f"Portfolio history loaded from {self.portfolio_history_file}")
        except FileNotFoundError:
            logging.error(f"Error: The file {self.portfolio_history_file} was not found.")
            self.portfolio_history = None
        except Exception as e:
            logging.error(f"An error occurred while loading the portfolio history: {e}")
            self.portfolio_history = None

    def plot_equity_curve(self):
        """
        Plots the equity curve (total portfolio value over time).
        """
        if self.portfolio_history is None or 'total' not in self.portfolio_history.columns:
            logging.error("Portfolio history is not loaded or is missing the 'total' column.")
            return

        plt.figure(figsize=(12, 8))
        plt.plot(self.portfolio_history.index, self.portfolio_history['total'], label='Equity Curve')
        plt.title('Portfolio Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value ($)')
        plt.legend()
        plt.grid(True)
        plt.savefig('equity_curve.png')
        logging.info("Equity curve plot saved to equity_curve.png")
        plt.show()