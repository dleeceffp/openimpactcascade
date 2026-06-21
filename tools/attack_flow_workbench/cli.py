"""CLI entry point for the Attack Flow Workbench.

Supports two modes:

  Single-path (default):
    python cli.py -i healthcare -r "United States" -s "500-1000"
    Generates one attack flow for the given industry/region/org-size.

  Multi-path (--asset / --target):
    python cli.py -i healthcare -r "United States" -s "500-1000" \\
        --asset "patient records database" \\
        --target "unauthorized exfiltration of patient PII" \\
        --entries "guest WiFi" "contractor VPN"
    Evaluates multiple entry points against the fixed terminal and produces
    per-route STIX bundles + a narrative summary.md (OIC-DESIGN-2026-044).
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from config import DEFAULT_OUTPUT_DIR
from formatter import AttackFlowFormatter

# Defer heavy imports until needed so --help works without all dependencies
AttackFlowGenerator = None
MultiPathGenerator = None
write_run_output = None


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MITRE Attack Flow Generation Workbench",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single-path: generate one attack flow (default mode)
  python cli.py -i healthcare -r "United States" -s "500-1000"

  # Single-path with provider override
  python cli.py -i financial -r Canada -s SME --provider anthropic --weight heavy

  # Multi-path: evaluate multiple entry points against a protected terminal
  python cli.py -i healthcare -r "United States" -s Enterprise \\
      --asset "patient records database" \\
      --target "unauthorized exfiltration of patient PII"

  # Multi-path with named entries and path-count control
  python cli.py -i healthcare -r "United States" -s Enterprise \\
      --asset "patient records database" \\
      --target "unauthorized exfiltration of patient PII" \\
      --entries "guest WiFi" "contractor VPN" \\
      --target-paths 4 --max-paths 8

  # Offline run (no web search)
  python cli.py -i healthcare -r "United States" -s Enterprise \\
      --asset "patient records database" \\
      --target "unauthorized exfiltration of patient PII" \\
      --no-web-search
        """,
    )

    # ----------------------------------------------------------------
    # Required (both modes)
    # ----------------------------------------------------------------
    parser.add_argument("--industry", "-i", required=True,
                        help="Industry sector (e.g. healthcare, financial, manufacturing)")
    parser.add_argument("--region", "-r", required=True,
                        help="Region/country (e.g. 'United States', Canada, UK)")
    parser.add_argument("--org-size", "-s", required=True,
                        help="Organization size (e.g. SME, Enterprise, '500-1000')")

    # ----------------------------------------------------------------
    # Multi-path mode (presence of --asset activates it)
    # ----------------------------------------------------------------
    multi = parser.add_argument_group("Multi-path mode (--asset required)")
    multi.add_argument(
        "--asset", "-a",
        default=None,
        help="Protected asset to analyse (e.g. 'patient records database'). "
             "Activates multi-path mode.",
    )
    multi.add_argument(
        "--target",
        default=None,
        dest="terminal",
        metavar="TERMINAL",
        help="Terminal compromise outcome (e.g. 'unauthorized exfiltration of patient PII'). "
             "Defaults to '<asset> compromise' when --asset is set.",
    )
    multi.add_argument(
        "--entries",
        nargs="+",
        default=None,
        metavar="ENTRY",
        help="Named entry points to evaluate (always get a verdict). "
             "Tool also evaluates default archetypes. "
             "Example: --entries 'guest WiFi' 'contractor VPN'",
    )
    multi.add_argument(
        "--min-paths",
        type=int,
        default=2,
        help="Minimum credible routes to aim for (default: 2)",
    )
    multi.add_argument(
        "--target-paths",
        type=int,
        default=3,
        help="Target number of credible routes (default: 3)",
    )
    multi.add_argument(
        "--max-paths",
        type=int,
        default=None,
        help="Hard cap on credible routes (default: OIC_MAX_PATHS env var or 10)",
    )

    # ----------------------------------------------------------------
    # Single-path options
    # ----------------------------------------------------------------
    single = parser.add_argument_group("Single-path options")
    single.add_argument("--threat", "-t",
                        help="Specific threat scenario (single-path mode)")
    single.add_argument(
        "--format", "-f",
        choices=["stix", "json", "md", "markdown", "both"],
        default="stix",
        help="Output format for single-path mode (default: stix)",
    )

    # ----------------------------------------------------------------
    # Shared options
    # ----------------------------------------------------------------
    parser.add_argument("--output", "-o", type=Path, default=Path(DEFAULT_OUTPUT_DIR),
                        help=f"Output base directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--provider", choices=["anthropic", "openai", "gemini"], default=None,
                        help="LLM provider (default: OIC_LLM_PROVIDER env / oic_llm config)")
    parser.add_argument("--weight", choices=["light", "heavy"], default=None,
                        help="Model weight/tier (default: OIC_LLM_WEIGHT env / oic_llm config)")
    parser.add_argument(
        "--search-provider",
        choices=["tavily", "brave", "null"],
        default=None,
        dest="search_provider",
        help="Search provider (default: OIC_SEARCH_PROVIDER env, typically tavily). "
             "Use 'null' to disable.",
    )
    parser.add_argument("--no-web-search", action="store_true",
                        help="Disable web search for recent threat intelligence")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    """Main entry point."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger("oic.attack_flow.cli")

    _check_environment()  # warns only — oic_llm raises typed errors at call time

    include_search = not args.no_web_search and args.search_provider != "null"
    effective_search = args.search_provider if args.search_provider != "null" else None

    # Dispatch to mode
    if args.asset:
        return _run_multi_path(args, logger, include_search, effective_search)
    else:
        return _run_single_path(args, logger, include_search, effective_search)


# ---------------------------------------------------------------------------
# Single-path mode
# ---------------------------------------------------------------------------

def _run_single_path(args, logger, include_search: bool, effective_search: Optional[str]) -> int:
    logger.info("=" * 70)
    logger.info("MITRE Attack Flow Workbench — Single-path mode")
    logger.info("=" * 70)
    logger.info(f"Industry: {args.industry}")
    logger.info(f"Region: {args.region}")
    logger.info(f"Organization Size: {args.org_size}")
    if args.threat:
        logger.info(f"Threat Scenario: {args.threat}")
    logger.info(f"LLM: provider={args.provider or 'env/config'}  weight={args.weight or 'env/config'}")
    logger.info(f"Search: {'disabled' if not include_search else (effective_search or 'env/config')}")
    logger.info("=" * 70)

    try:
        global AttackFlowGenerator
        if AttackFlowGenerator is None:
            from attack_flow_generator import AttackFlowGenerator

        generator = AttackFlowGenerator(
            provider=args.provider,
            weight=args.weight,
            search_provider=effective_search,
        )

        flow_data = generator.generate_flow(
            industry=args.industry,
            region=args.region,
            organization_size=args.org_size,
            threat_scenario=args.threat,
            include_web_search=include_search,
        )

        filename_base = AttackFlowFormatter.generate_filename(
            args.industry, args.region, args.org_size, suffix=""
        )

        saved_files = []
        args.output.mkdir(parents=True, exist_ok=True)

        if args.format in ("stix", "json", "both"):
            p = AttackFlowFormatter.save_to_file(
                flow_data, args.output / filename_base, format="stix"
            )
            saved_files.append(p)
            logger.info(f"STIX bundle saved: {p}")

        if args.format in ("md", "markdown", "both"):
            p = AttackFlowFormatter.save_to_file(
                flow_data, args.output / filename_base, format="md"
            )
            saved_files.append(p)
            logger.info(f"Markdown saved: {p}")

        viewer_src = Path(__file__).parent / "attack_flow_viewer.html"
        if viewer_src.exists():
            import shutil
            viewer_dst = args.output / "attack_flow_viewer.html"
            try:
                shutil.copy2(viewer_src, viewer_dst)
                saved_files.append(viewer_dst)
            except Exception as e:
                logger.warning(f"Could not copy viewer: {e}")

        print("\n" + "=" * 70)
        print("ATTACK FLOW GENERATED SUCCESSFULLY")
        print("=" * 70)
        print(AttackFlowFormatter.to_summary_markdown(flow_data))
        print("=" * 70)
        print("\nFiles saved to:")
        for f in saved_files:
            print(f"  - {f}")
        print("\nView: open attack_flow_viewer.html and load the .json file.")
        return 0

    except KeyboardInterrupt:
        logger.info("Cancelled")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


# ---------------------------------------------------------------------------
# Multi-path mode
# ---------------------------------------------------------------------------

def _run_multi_path(args, logger, include_search: bool, effective_search: Optional[str]) -> int:
    import re
    from datetime import datetime

    asset = args.asset
    terminal = args.terminal or f"{asset} compromise"

    logger.info("=" * 70)
    logger.info("MITRE Attack Flow Workbench — Multi-path mode (OIC-DESIGN-2026-044)")
    logger.info("=" * 70)
    logger.info(f"Asset / terminal: {asset}  →  {terminal}")
    logger.info(f"Industry: {args.industry}  Region: {args.region}  Size: {args.org_size}")
    if args.entries:
        logger.info(f"Named entries: {args.entries}")
    logger.info(f"Path bounds: min={args.min_paths} target={args.target_paths} max={args.max_paths or 'env/10'}")
    logger.info(f"LLM: provider={args.provider or 'env/config'}  weight={args.weight or 'env/config'}")
    logger.info(f"Search: {'disabled' if not include_search else (effective_search or 'env/config')}")
    logger.info("=" * 70)

    try:
        global MultiPathGenerator, write_run_output
        if MultiPathGenerator is None:
            from multi_path_generator import MultiPathGenerator
        if write_run_output is None:
            from multi_path_formatter import write_run_output

        generator = MultiPathGenerator(
            provider=args.provider,
            weight=args.weight,
            search_provider=effective_search,
            min_paths=args.min_paths,
            target_paths=args.target_paths,
            max_paths=args.max_paths,
        )

        result = generator.generate(
            asset=asset,
            terminal=terminal,
            industry=args.industry,
            region=args.region,
            organization_size=args.org_size,
            named_entries=args.entries,
            include_web_search=include_search,
        )

        # Build per-run output directory: <base>/<asset-slug>_<timestamp>/
        asset_slug = re.sub(r"[^a-z0-9]+", "_", asset.lower()).strip("_")[:30]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = args.output / f"{asset_slug}_{ts}"

        viewer_src = Path(__file__).parent / "attack_flow_viewer.html"
        written = write_run_output(
            result=result,
            output_dir=run_dir,
            viewer_src=viewer_src if viewer_src.exists() else None,
        )

        # Console summary
        n_credible = len(result.credible_routes)
        n_no_path = len(result.no_path_routes)
        n_diff = len(result.different_terminal_routes)

        print("\n" + "=" * 70)
        print(f"MULTI-PATH ANALYSIS COMPLETE: {asset}")
        print("=" * 70)
        print(f"Terminal: {terminal}")
        print(f"Model: {result.llm_provider} / {result.llm_model}")
        print()
        print(f"  Credible routes:          {n_credible}")
        print(f"  No credible path:         {n_no_path}")
        print(f"  Different terminal:       {n_diff}")
        print()

        if result.credible_routes:
            print("Credible routes:")
            for i, r in enumerate(result.credible_routes, 1):
                n_actions = len((r.flow_data or {}).get("attack_actions", []))
                print(f"  {i}. {r.entry_label}  ({n_actions} actions)")

        if result.no_path_routes:
            print("\nMonitored assumptions (ruled out — see summary.md for flip conditions):")
            for r in result.no_path_routes:
                print(f"  - {r.entry_label}")

        print("\nFiles written:")
        for f in written:
            print(f"  - {f}")

        print(f"\nFull narrative: {run_dir / 'summary.md'}")
        print("View bundles: open attack_flow_viewer.html in the run directory.")
        return 0

    except KeyboardInterrupt:
        logger.info("Cancelled")
        return 130
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


# ---------------------------------------------------------------------------
# Environment check
# ---------------------------------------------------------------------------

def _check_environment() -> bool:
    """Warn if no LLM or search credentials are present. Never hard-fails."""
    import os

    has_llm = any([
        os.environ.get("ANTHROPIC_API_KEY"),
        os.environ.get("OPENAI_API_KEY"),
        os.environ.get("GEMINI_API_KEY"),
        os.environ.get("GOOGLE_API_KEY"),
    ])
    if not has_llm:
        print("Warning: No LLM API key found (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY).")
        print("Set the key for your chosen provider before generating a flow.")

    has_search = any([
        os.environ.get("TAVILY_API_KEY"),
        os.environ.get("BRAVE_SEARCH_API_KEY"),
    ])
    if not has_search:
        print("Note: No search API key found (TAVILY_API_KEY / BRAVE_SEARCH_API_KEY).")
        print("Web search grounding will be skipped; use --no-web-search to silence this.")

    corpus_dir = Path(__file__).parent.parent.parent / "app" / "corpus" / "ref_pillars"
    if not corpus_dir.exists():
        print(f"Warning: Corpus directory not found at {corpus_dir}")
        print("Threat intelligence grounding may be limited.")

    return True  # always proceed — oic_llm raises precise errors at call time


if __name__ == "__main__":
    sys.exit(main())
