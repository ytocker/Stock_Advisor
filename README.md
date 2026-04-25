# AI Stock Advisor

An AI-powered weekly stock screening system that uses an OpenAI agent to analyze the S&P 500 universe and produce a ranked report of the top 10 stocks worth acting on.

---

## What It Does

Each run the agent:
1. Fetches the full S&P 500 ticker list from Wikipedia
2. Screens stocks by KPIs (market cap, price, trading volume, P/E ratio, sector)
3. Checks sector-level performance trends
4. Deep-dives into candidate fundamentals (revenue growth, margins, debt, EPS) and price momentum
5. Ranks and selects the top 10 stocks
6. Writes a Markdown report with an action (BUY / HOLD / WATCH), investment thesis, key metrics, and risk factors for each pick

---

## Agent Architecture

```
main.py
  └── run_agent()               <- OpenAI GPT-4o with function calling
        │
        ├── get_stock_universe()       fetch ~503 S&P 500 tickers
        ├── screen_stocks()            batch-filter by KPIs (yfinance)
        ├── get_sector_performance()   sector trend via SPDR ETFs
        ├── get_stock_details()        full fundamentals per stock
        └── get_price_history()        1mo/3mo/6mo/1y price changes
              │
        report.py -> reports/report_YYYY-MM-DD.md
```

The agent runs a loop (up to 25 iterations) where it autonomously decides which tools to call, which tickers to investigate, and how to rank the final picks — guided by the selected strategy prompt.

---

## Capabilities

| Feature | Detail |
|---|---|
| Stock universe | S&P 500 (~503 stocks) |
| Data source | Yahoo Finance via `yfinance` (free, no API key) |
| KPI filters | Market cap, price, avg daily volume, P/E ratio, sector |
| Fundamentals | P/E, EPS, revenue growth, margins, debt/equity, free cash flow, dividend yield, beta |
| Momentum | 1-month, 3-month, 6-month, 1-year price change; 52-week average comparison |
| Sector context | Performance of 11 GICS sectors via SPDR ETFs |
| Strategies | 4 built-in (balanced, value, growth, momentum); easily extensible |
| Output | Markdown report with summary table + per-stock analysis |
| Runtime | ~5-10 minutes per run |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your OpenAI API key

```bash
cp .env.example .env
# Edit .env and set your key:
# OPENAI_API_KEY=sk-...
```

### 3. Run

```bash
python main.py
```

---

## CLI Usage

```
python main.py [--strategy NAME] [--model MODEL] [--verbose]
```

| Flag | Default | Description |
|---|---|---|
| `--strategy` | `balanced` | Strategy to use (see below) |
| `--model` | `gpt-4o` | OpenAI model override |
| `--verbose` | off | Print agent iterations and tool call logs |

### Examples

```bash
# Default: balanced value + momentum strategy
python main.py

# Deep value picks, with verbose logging
python main.py --strategy value --verbose

# High-growth screening using a cheaper model
python main.py --strategy growth --model gpt-4o-mini

# Price momentum strategy
python main.py --strategy momentum
```

---

## Built-in Strategies

| Key | Name | Description |
|---|---|---|
| `balanced` | Balanced Value + Momentum | Large/mid-cap, P/E <30, >10% revenue growth, high volume, positive momentum |
| `value` | Deep Value | P/E <15, P/B <2, market cap >$10B, dividend yield >1.5%, low debt |
| `growth` | High Growth | Revenue growth >20% YoY, expanding margins, forward-looking EPS, sectors: tech/health/consumer |
| `momentum` | Price Momentum | Strongest 6mo/1y performers, trading above 52-week average, high relative volume |

### Adding a New Strategy

Edit `config.py` and add an entry to the `STRATEGIES` dict:

```python
STRATEGIES["my_strategy"] = {
    "name": "My Custom Strategy",
    "description": (
        "Describe the criteria here. The agent reads this and applies it. "
        "Be specific: mention P/E thresholds, sectors, growth rates, etc."
    ),
}
```

Then run:

```bash
python main.py --strategy my_strategy
```

No other code changes required.

---

## Report Output

Reports are saved to `reports/report_YYYY-MM-DD.md`. Each report contains:

- **Market context** — brief summary of current conditions
- **Strategy application** — how the strategy was applied this run
- **Summary table** — all 10 picks at a glance (ticker, sector, price, market cap, P/E, volume, action)
- **Per-stock sections** — for each of the 10 picks:
  - Action: BUY / HOLD / WATCH
  - Investment thesis (3-5 sentences with specific data)
  - Key metrics table (revenue growth, margins, debt/equity, price momentum, dividend)
  - Risk factors
- **Portfolio summary** — cross-portfolio observations

---

## Project Structure

```
Stock_Advisor/
├── main.py          # Entry point
├── agent.py         # OpenAI agentic loop, tool definitions, system prompt
├── config.py        # Strategy definitions and model config
├── report.py        # Markdown report renderer
├── tools/
│   ├── data.py      # get_stock_universe, get_stock_details, get_price_history, get_sector_performance
│   └── screener.py  # screen_stocks (batch KPI filter)
├── reports/         # Generated reports (created on first run)
├── requirements.txt
└── .env.example
```

---

## Notes

- **Cost**: A full run with GPT-4o typically uses ~20-40k tokens (~$0.10-$0.30 per run).
- **Rate limits**: Yahoo Finance requests are deliberately paced (0.3s per ticker, 2s between batches) to avoid throttling.
- **Data freshness**: All data is fetched live from Yahoo Finance at run time.
- **Not financial advice**: Reports are for informational and research purposes only.
