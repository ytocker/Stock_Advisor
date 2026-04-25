import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Stock Advisor - weekly S&P 500 analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Strategies:
  balanced  Large/mid-cap, P/E <30, momentum, high volume (default)
  value     P/E <15, P/B <2, dividend yield >1.5%, large-cap
  growth    Revenue growth >20% YoY, expanding margins, tech/health
  momentum  Strongest 6mo/1y price performance, high volume

Examples:
  python main.py
  python main.py --strategy value --verbose
  python main.py --strategy growth --model gpt-4o-mini
        """,
    )
    parser.add_argument(
        "--strategy",
        default=None,
        metavar="NAME",
        help="Strategy key: balanced, value, growth, momentum (default: balanced)",
    )
    parser.add_argument(
        "--model",
        default=None,
        metavar="MODEL",
        help="OpenAI model override (default: gpt-4o)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print agent iterations and tool call logs",
    )
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "ERROR: OPENAI_API_KEY not set.\n"
            "Create a .env file with OPENAI_API_KEY=sk-... or export it as an environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    from config import DEFAULT_STRATEGY, MODEL, STRATEGIES
    from agent import run_agent
    from report import save_report

    strategy_key = args.strategy or DEFAULT_STRATEGY
    if strategy_key not in STRATEGIES:
        print(
            f"ERROR: Unknown strategy '{strategy_key}'.\n"
            f"Available strategies: {', '.join(STRATEGIES.keys())}",
            file=sys.stderr,
        )
        sys.exit(1)

    model = args.model or MODEL
    strategy_name = STRATEGIES[strategy_key]["name"]

    print("=" * 60)
    print("  AI Stock Advisor")
    print("=" * 60)
    print(f"  Strategy : {strategy_name}")
    print(f"  Model    : {model}")
    print(f"  Verbose  : {args.verbose}")
    print("=" * 60)
    print()
    print("Starting agent... (this may take 5-10 minutes)")
    print()

    try:
        result = run_agent(
            strategy_key=strategy_key,
            model=model,
            verbose=args.verbose,
        )
    except RuntimeError as e:
        print(f"\nERROR: Agent failed: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(1)

    filepath = save_report(result, strategy_name)

    print()
    print("=" * 60)
    print(f"  Report saved: {filepath}")
    print("=" * 60)


if __name__ == "__main__":
    main()
