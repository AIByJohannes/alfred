from __future__ import annotations

import argparse
import json

from ddgs import DDGS


def run_research(query: str, *, max_results: int = 5) -> dict[str, object]:
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=max_results))
    return {"query": query, "results": results}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.research",
        description="Run a quick web-grounded research query.",
    )
    parser.add_argument("query")
    parser.add_argument("--max-results", type=int, default=5)
    args = parser.parse_args()
    print(json.dumps(run_research(args.query, max_results=args.max_results), indent=2))


if __name__ == "__main__":
    main()
