import logging
import os
import pandas as pd
from external_data_client import fetch_news_data # Import the new function

class NewsFetcher:
    def __init__(self, data_dir="historical_data"):
        """Initializes the NewsFetcher."""
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
        if not self.api_key:
            logging.error("ALPHA_VANTAGE_API_KEY environment variable not set.")
            raise ValueError("ALPHA_VANTAGE_API_KEY not found in environment variables.")
        logging.info("NewsFetcher initialized to use Alpha Vantage.")

    def fetch_news_and_analyze_sentiment(self, symbol, start_date=None, end_date=None):
        """
        Fetches news and sentiment for a given symbol using Alpha Vantage.
        The start_date and end_date arguments are ignored as the API returns recent news.

        Args:
            symbol (str): The financial instrument to fetch news for (e.g., EURUSD).
            start_date (str, optional): Ignored.
            end_date (str, optional): Ignored.

        Returns:
            pd.DataFrame: A DataFrame with news headlines and their pre-calculated sentiment scores.
        """
        logging.info(f"Fetching news for {symbol} from Alpha Vantage.")
        
        # Fetch data using the new client
        df = fetch_news_data(symbol, self.api_key)

        if df is None or df.empty:
            logging.warning(f"No news found for {symbol} from Alpha Vantage.")
            return pd.DataFrame()

        # The client already returns the dataframe in the desired format with columns:
        # ['timestamp', 'type', 'symbol', 'sentiment', 'headline']
        # For compatibility with the consumer, ensure all original columns are present, even if empty.
        if 'keywords' not in df.columns:
            df['keywords'] = [[] for _ in range(len(df))]
        if 'themes' not in df.columns:
            df['themes'] = [[] for _ in range(len(df))]

        processed_df = df[['timestamp', 'type', 'symbol', 'sentiment', 'headline', 'keywords', 'themes']]

        logging.info(f"Successfully fetched and processed {len(processed_df)} news articles from Alpha Vantage.")

        return processed_df

    def save_events_to_csv(self, df, filename="real_events.csv"):
        """
        Saves a DataFrame of events to a CSV file.

        Args:
            df (pd.DataFrame): The DataFrame to save.
            filename (str): The name of the file to save to.
        """
        if df is None or df.empty:
            logging.warning("DataFrame is empty. Nothing to save.")
            return

        filepath = os.path.join(self.data_dir, filename)
        df.to_csv(filepath, index=False)
        logging.info(f"Events saved to {filepath}")