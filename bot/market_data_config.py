import datetime

# Define market hours for different symbols.
# Times are in UTC.
# Format: {'SYMBOL': [('DAY_OF_WEEK', (START_HOUR, START_MINUTE), (END_HOUR, END_MINUTE)), ...] }
# DAY_OF_WEEK: 0=Monday, 6=Sunday

MARKET_HOURS = {
    'EURUSD': [
        (0, (0, 0), (23, 59)), # Monday 00:00 to 23:59
        (1, (0, 0), (23, 59)), # Tuesday
        (2, (0, 0), (23, 59)), # Wednesday
        (3, (0, 0), (23, 59)), # Thursday
        (4, (0, 0), (21, 0))  # Friday 00:00 to 21:00 (closes early)
    ],
    'XAUUSD': [
        (0, (0, 0), (23, 59)), # Monday 00:00 to 23:59
        (1, (0, 0), (23, 59)), # Tuesday
        (2, (0, 0), (23, 59)), # Wednesday
        (3, (0, 0), (23, 59)), # Thursday
        (4, (0, 0), (21, 0))  # Friday 00:00 to 21:00 (closes early)
    ],
    'GBPUSD': [
        (0, (0, 0), (23, 59)), # Monday 00:00 to 23:59
        (1, (0, 0), (23, 59)), # Tuesday
        (2, (0, 0), (23, 59)), # Wednesday
        (3, (0, 0), (23, 59)), # Thursday
        (4, (0, 0), (21, 0))  # Friday 00:00 to 21:00 (closes early)
    ],
    # Add more symbols and their market hours as needed
}

# Example of a symbol with limited hours (e.g., a stock that trades 9:30-16:00 EST, converted to UTC)
# Assuming EST is UTC-5, so 9:30 EST is 14:30 UTC, and 16:00 EST is 21:00 UTC
# 'AAPL': [
#     (0, (14, 30), (21, 0)), # Monday
#     (1, (14, 30), (21, 0)), # Tuesday
#     (2, (14, 30), (21, 0)), # Wednesday
#     (3, (14, 30), (21, 0)), # Thursday
#     (4, (14, 30), (21, 0))  # Friday
# ],
