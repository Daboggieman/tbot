import logging

class ThematicAnalyzer:
    """
    Analyzes lists of keywords to identify and categorize them into predefined market themes.
    """

    def __init__(self):
        """
        Initializes the ThematicAnalyzer with a predefined set of themes and their associated keywords.
        
        The theme dictionary uses the theme name as the key and a list of keyword stems as the value.
        This allows for simple and fast matching.
        """
        self.themes = {
            "Monetary Policy": ["fed", "rate", "inflation", "ecb", "interest", "cpi"],
            "Geopolitical Risk": ["war", "conflict", "tension", "sanction", "geopolitical"],
            "Technology": ["ai", "tech", "software", "hardware", "innovation"],
            "Corporate Earnings": ["earning", "profit", "revenue", "guidance", "forecast"],
            "Market Sentiment": ["bullish", "bearish", "optimism", "pessimism", "risk-on", "risk-off"],
            "Apple Specific": ["iphone", "aapl", "tim cook", "macbook", "icloud", "apple store"]
        }
        logging.info("ThematicAnalyzer initialized with predefined themes.")

    def analyze_themes(self, keywords: list) -> list:
        """
        Analyzes a list of keywords and returns a list of detected themes.

        Args:
            keywords (list): A list of keyword strings from a news article.

        Returns:
            list: A list of unique theme names that were matched.
        """
        detected_themes = set()
        if not keywords:
            return []

        for keyword in keywords:
            keyword_lower = keyword.lower()
            for theme, theme_keywords in self.themes.items():
                for theme_key in theme_keywords:
                    if theme_key in keyword_lower:
                        detected_themes.add(theme)
                        break # Move to the next keyword once a theme is found for it
        
        return list(detected_themes)
