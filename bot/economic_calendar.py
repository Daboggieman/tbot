'''
This module is responsible for fetching and processing economic calendar data using the investpy library.
It will provide functions to get upcoming economic events, which can be used by the trading bot
to make decisions based on market-moving news.
'''

import investpy
import pandas as pd
from datetime import datetime, timedelta

def get_economic_events(days_ahead=7):
    """
    Fetches economic events for the upcoming number of days.

    Args:
        days_ahead (int): The number of days ahead to fetch events for.

    Returns:
        pandas.DataFrame: A DataFrame containing the economic events, 
                          sorted by time. Returns an empty DataFrame on error.
    """
    try:
        # We fetch for today + days_ahead
        to_date = (datetime.now() + timedelta(days=days_ahead)).strftime('%d/%m/%Y')
        from_date = datetime.now().strftime('%d/%m/%Y')

        # Fetch data using investpy
        events_df = investpy.economic_calendar(
            from_date=from_date,
            to_date=to_date
        )

        # Clean and format the DataFrame
        if not events_df.empty:
            events_df['time'] = pd.to_datetime(events_df['time'], format='%H:%M', errors='coerce').dt.time
            events_df = events_df.sort_values(by=['date', 'time'])
            events_df = events_df.reset_index(drop=True)
        
        return events_df

    except Exception as e:
        print(f"Error fetching economic events: {e}")
        return pd.DataFrame() # Return empty DataFrame on failure

if __name__ == '__main__':
    # Example usage: Get events for the next week
    print("Fetching economic events for the next 7 days...")
    upcoming_events = get_economic_events(days_ahead=7)

    if not upcoming_events.empty:
        print("Successfully fetched events:")
        # Displaying only high-impact events for clarity
        high_impact_events = upcoming_events[upcoming_events['importance'] == 'high']
        if not high_impact_events.empty:
            print("\n--- High Impact Events ---")
            print(high_impact_events[['date', 'time', 'currency', 'event', 'importance']])
        else:
            print("\nNo high impact events found in the next 7 days.")
    else:
        print("Could not fetch economic events.")