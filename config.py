MODEL = "gpt-4o"
MAX_AGENT_ITERATIONS = 25

STRATEGIES: dict[str, dict] = {
    "balanced": {
        "name": "Balanced Value + Momentum",
        "description": (
            "Focus on large-cap and mid-cap stocks with reasonable valuations "
            "(P/E under 30), positive price momentum over 3-6 months, strong "
            "revenue growth (>10% YoY), healthy balance sheets (debt/equity < 1.5), "
            "and high average daily volume (> 1M shares). Prefer companies with "
            "consistent EPS growth and net margins above 10%."
        ),
    },
    "value": {
        "name": "Deep Value",
        "description": (
            "Seek undervalued stocks with P/E below 15, price-to-book below 2, "
            "market cap over $10B, dividend yield above 1.5%, and average daily "
            "volume above 500K shares. Prioritize companies with stable or growing "
            "free cash flow and low debt-to-equity ratios."
        ),
    },
    "growth": {
        "name": "High Growth",
        "description": (
            "Target companies with revenue growth above 20% YoY, expanding gross "
            "margins, and strong forward EPS estimates. Accept higher P/E ratios "
            "(up to 60) for companies in fast-growing sectors like technology, "
            "healthcare, and consumer discretionary. Minimum market cap $5B."
        ),
    },
    "momentum": {
        "name": "Price Momentum",
        "description": (
            "Select stocks with the strongest 6-month and 1-year price performance, "
            "high relative volume, and recent positive earnings surprises. Filter for "
            "stocks trading above their 52-week average. Market cap minimum $2B."
        ),
    },
}

DEFAULT_STRATEGY = "balanced"
