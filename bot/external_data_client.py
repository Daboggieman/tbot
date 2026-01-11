import requests
import pandas as pd
import logging

BASE_URL = "https://www.alphavantage.co/query"



def fetch_news_data(symbol: str, api_key: str):
    """
    Fetches news and sentiment data from Alpha Vantage.

    Args:
        symbol (str): The forex pair (e.g., EURUSD).
        api_key (str): The Alpha Vantage API key.

    Returns:
        pd.DataFrame: A DataFrame with news and sentiment, or an empty DataFrame on error.
    """
    logging.info(f"Fetching news and sentiment for {symbol} from Alpha Vantage...")
    
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": symbol,
        "limit": "200",  # Max results per request
        "apikey": api_key,
    }

    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()

        if "Error Message" in data or "feed" not in data:
            logging.error(f"Alpha Vantage API error for news data: {data.get('Error Message', 'Unexpected format')}")
            return pd.DataFrame()

        feed = data.get('feed', [])
        if not feed:
            logging.warning(f"No news found for {symbol} from Alpha Vantage.")
            return pd.DataFrame()

        df = pd.DataFrame(feed)

        # Extract the ticker sentiment score
        def get_ticker_sentiment(tickers, target_ticker):
            for ticker_sentiment in tickers:
                if ticker_sentiment['ticker'] == target_ticker:
                    return float(ticker_sentiment['ticker_sentiment_score'])
            return 0.0

        df['sentiment'] = df['ticker_sentiment'].apply(lambda x: get_ticker_sentiment(x, symbol))
        df.rename(columns={'title': 'headline', 'time_published': 'timestamp'}, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y%m%dT%H%M%S').dt.tz_localize(None)
        df['symbol'] = symbol
        df['type'] = 'news'

        logging.info(f"Successfully fetched {len(df)} news articles for {symbol}.")
        return df[['timestamp', 'type', 'symbol', 'sentiment', 'headline']]

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching news data from Alpha Vantage: {e}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"An error occurred processing news data: {e}")
        return pd.DataFrame()
