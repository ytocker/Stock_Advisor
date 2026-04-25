import json
import re
from datetime import date

import openai

from config import MAX_AGENT_ITERATIONS, STRATEGIES, DEFAULT_STRATEGY, MODEL
from tools.data import (
    DataFetchError,
    get_price_history,
    get_sector_performance,
    get_stock_details,
    get_stock_universe,
)
from tools.screener import screen_stocks

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_universe",
            "description": (
                "Returns the list of all S&P 500 ticker symbols scraped from Wikipedia. "
                "Call this first to get the full universe before screening. "
                "Returns approximately 503 tickers."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "screen_stocks",
            "description": (
                "Filters a list of tickers by fundamental KPIs using Yahoo Finance. "
                "Pass only filters relevant to the current strategy. "
                "Returns a summary list of passing stocks. "
                "WARNING: passing >200 tickers at once is slow - prefer sector-filtered subsets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of ticker symbols to screen.",
                    },
                    "min_market_cap": {
                        "type": "number",
                        "description": "Minimum market cap in USD (e.g. 10000000000 for $10B).",
                    },
                    "max_market_cap": {
                        "type": "number",
                        "description": "Maximum market cap in USD.",
                    },
                    "min_price": {
                        "type": "number",
                        "description": "Minimum stock price in USD.",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum stock price in USD.",
                    },
                    "min_avg_volume": {
                        "type": "number",
                        "description": "Minimum average daily trading volume (shares).",
                    },
                    "max_pe_ratio": {
                        "type": "number",
                        "description": "Maximum trailing P/E ratio.",
                    },
                    "sector": {
                        "type": "string",
                        "description": (
                            "Filter to a single GICS sector: Technology, Health Care, "
                            "Financials, Consumer Discretionary, Consumer Staples, "
                            "Energy, Industrials, Materials, Real Estate, Utilities, "
                            "Communication Services."
                        ),
                    },
                },
                "required": ["tickers"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_details",
            "description": (
                "Returns comprehensive fundamental data for a single stock: "
                "P/E, EPS, revenue/earnings growth, margins, debt/equity, "
                "52-week range, dividend yield, beta, and a business description. "
                "Call this for each candidate after initial screening."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker, e.g. 'AAPL'."},
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_price_history",
            "description": (
                "Returns percentage price changes over 1 month, 3 months, 6 months, "
                "and 1 year for a stock, plus whether it trades above its 52-week average. "
                "Use to assess momentum and trend."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol."},
                    "period": {
                        "type": "string",
                        "enum": ["1mo", "3mo", "6mo", "1y"],
                        "description": "Lookback period hint (internally always fetches 1y).",
                    },
                },
                "required": ["ticker"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sector_performance",
            "description": (
                "Returns recent performance (1mo/3mo/6mo/1y % change) for a GICS sector "
                "using its representative SPDR ETF as a proxy. "
                "Use to assess sector tailwinds and headwinds."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "description": (
                            "GICS sector: Technology, Health Care, Financials, "
                            "Consumer Discretionary, Consumer Staples, Energy, "
                            "Industrials, Materials, Real Estate, Utilities, "
                            "Communication Services."
                        ),
                    },
                },
                "required": ["sector"],
            },
        },
    },
]

_TOOL_DISPATCH = {
    "get_stock_universe": lambda args: get_stock_universe(),
    "get_stock_details": lambda args: get_stock_details(args["ticker"]),
    "get_price_history": lambda args: get_price_history(args["ticker"], args.get("period", "1y")),
    "get_sector_performance": lambda args: get_sector_performance(args["sector"]),
    "screen_stocks": lambda args: screen_stocks(
        tickers=args["tickers"],
        min_market_cap=args.get("min_market_cap"),
        max_market_cap=args.get("max_market_cap"),
        min_price=args.get("min_price"),
        max_price=args.get("max_price"),
        min_avg_volume=args.get("min_avg_volume"),
        max_pe_ratio=args.get("max_pe_ratio"),
        sector=args.get("sector"),
    ),
}


def _execute_tool(name: str, args: dict) -> str:
    fn = _TOOL_DISPATCH.get(name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: {name}"})
    try:
        return json.dumps(fn(args), default=str)
    except DataFetchError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"Unexpected error in {name}: {e}"})


def _build_system_prompt(strategy_name: str, strategy_description: str, today: str) -> str:
    return f"""You are an expert stock analyst and portfolio manager running a weekly stock screening process.

Today's date: {today}

## Your Mission
Analyze the S&P 500 universe and produce a ranked list of the top 10 stocks to recommend to investors, following the strategy below.

## Investment Strategy: {strategy_name}
{strategy_description}

## Required Process (follow these steps in order)

### Step 1: Get the Universe
Call get_stock_universe() to retrieve all S&P 500 tickers.

### Step 2: Screen for Candidates
Call screen_stocks() with filters matching the strategy. To avoid timeouts:
- Run 2-3 screening passes, each targeting a different sector or market-cap band
- Do NOT pass all 500+ tickers in a single call
- Aim to narrow down to 20-40 candidates total

### Step 3: Sector Context
For each major sector you're considering, call get_sector_performance() to understand macro tailwinds and headwinds.

### Step 4: Deep Dive on Candidates
For each candidate from Step 2:
- Call get_stock_details() for fundamental analysis
- Call get_price_history() for momentum assessment
- Discard candidates that don't meet the strategy criteria on closer inspection

### Step 5: Rank and Select Top 10
Rank surviving candidates using the strategy criteria. Select the best 10.

### Step 6: Produce Final Output
Return a single JSON object (raw JSON only, no markdown fences) in exactly this schema:

{{
  "market_context": "<2-3 sentence summary of current market conditions>",
  "strategy_summary": "<1-2 sentence description of how the strategy was applied>",
  "stocks": [
    {{
      "rank": 1,
      "ticker": "AAPL",
      "name": "Apple Inc.",
      "sector": "Technology",
      "price": 185.50,
      "market_cap_billions": 2850.0,
      "pe_ratio": 28.5,
      "avg_volume_millions": 55.3,
      "action": "BUY",
      "thesis": "<3-5 sentence investment thesis citing actual numbers from the data>",
      "key_metrics": {{
        "revenue_growth_pct": 12.5,
        "net_margin_pct": 25.3,
        "debt_to_equity": 1.2,
        "change_6mo_pct": 18.4,
        "change_1y_pct": 32.1,
        "dividend_yield_pct": 0.5
      }},
      "risk_factors": "<2-3 sentence description of key risks>"
    }}
  ],
  "summary": "<3-4 sentence portfolio-level summary>"
}}

## Rules
- action must be one of: BUY, HOLD, WATCH
- thesis must cite actual numbers from the data you retrieved
- Do not recommend a stock without first calling get_stock_details() for it
- If a tool returns an error, skip that ticker and continue
- You must return exactly 10 stocks
- Return ONLY the JSON object as your final message - no other text
"""


def run_agent(
    strategy_key: str = DEFAULT_STRATEGY,
    model: str = MODEL,
    verbose: bool = False,
) -> dict:
    """
    Run the agentic loop and return the parsed JSON result dict.
    Raises RuntimeError if the agent fails to produce valid JSON
    within MAX_AGENT_ITERATIONS.
    """
    client = openai.OpenAI()

    strategy = STRATEGIES[strategy_key]
    today = date.today().isoformat()
    system_prompt = _build_system_prompt(strategy["name"], strategy["description"], today)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Please run the full stock screening process for the "
                f"'{strategy['name']}' strategy and produce the top 10 stock report."
            ),
        },
    ]

    for iteration in range(MAX_AGENT_ITERATIONS):
        if verbose:
            print(f"[agent] iteration {iteration + 1}/{MAX_AGENT_ITERATIONS}")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.2,
            max_tokens=4096,
        )

        choice = response.choices[0]
        message = choice.message
        messages.append(message.model_dump(exclude_none=True))

        if choice.finish_reason == "stop":
            content = (message.content or "").strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", content, re.DOTALL)
                if match:
                    return json.loads(match.group())
                raise RuntimeError(
                    f"Agent returned non-JSON final message: {content[:300]}"
                )

        if choice.finish_reason == "tool_calls":
            for tc in message.tool_calls or []:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)
                if verbose:
                    print(f"  [tool] {fn_name}({list(fn_args.keys())})")
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": _execute_tool(fn_name, fn_args),
                })
            continue

        raise RuntimeError(
            f"Unexpected finish_reason '{choice.finish_reason}' at iteration {iteration + 1}"
        )

    raise RuntimeError(
        f"Agent did not complete within {MAX_AGENT_ITERATIONS} iterations."
    )
