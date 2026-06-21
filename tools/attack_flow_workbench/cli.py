"""CLI entry point for the Attack Flow Workbench."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from config import DEFAULT_OUTPUT_DIR
from formatter import AttackFlowFormatter

# Defer import of attack_flow_generator until needed (handles missing dependencies for --help)
AttackFlowGenerator = None


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MITRE Attack Flow Generation Workbench - Generate industry-specific attack flows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate using default provider (oic_llm env/config) with Tavily search
  python cli.py --industry healthcare --region "United States" --org-size "500-1000"

  # Generate with a specific LLM provider and weight
  python cli.py --industry financial --region Canada --org-size SME \\
      --provider anthropic --weight heavy

  # Switch to Gemini, use Brave for search, output both STIX and markdown
  python cli.py --industry manufacturing --region UK --org-size Enterprise \\
      --provider gemini --weight heavy --search-provider brave --format both

  # Offline run — no web search
  python cli.py --industry healthcare --region "United States" --org-size Enterprise \\
      --no-web-search
        """
    )

    # Required arguments
    parser.add_argument(
        "--industry", "-i",
        required=True,
        help="Industry sector (e.g., healthcare, financial, manufacturing)"
    )
    parser.add_argument(
        "--region", "-r",
        required=True,
        help="Region/country (e.g., 'United States', Canada, UK)"
    )
    parser.add_argument(
        "--org-size", "-s",
        required=True,
        help="Organization size (e.g., SME, Enterprise, '500-1000')"
    )

    # Optional arguments
    parser.add_argument(
        "--threat", "-t",
        help="Specific threat scenario to model (optional)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["stix", "json", "md", "markdown", "both"],
        default="stix",
        help="Output format: stix (default, STIX 2.1 JSON bundle), json (alias for stix), md/markdown, both"
    )
    # LLM provider/weight overrides (default: oic_llm env/config)
    parser.add_argument(
        "--provider",
        choices=["anthropic", "openai", "gemini"],
        default=None,
        help="LLM provider to use (default: OIC_LLM_PROVIDER env var or oic_llm config)"
    )
    parser.add_argument(
        "--weight",
        choices=["light", "heavy"],
        default=None,
        help="Model weight/tier (default: OIC_LLM_WEIGHT env var or oic_llm config)"
    )
    # Search provider override
    parser.add_argument(
        "--search-provider",
        choices=["tavily", "brave", "null"],
        default=None,
        dest="search_provider",
        help="Search provider (default: OIC_SEARCH_PROVIDER env var, typically tavily). "
             "Use 'null' to disable search without --no-web-search."
    )
    parser.add_argument(
        "--no-web-search",
        action="store_true",
        help="Disable web search for recent threat intelligence"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    # Use UTF-8 for console output so Markdown summaries render correctly on Windows.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = parse_args()
    setup_logging(args.verbose)

    logger = logging.getLogger("oic.attack_flow.cli")

    # Validate environment
    if not _check_environment():
        return 1

    logger.info("=" * 70)
    logger.info("MITRE Attack Flow Generation Workbench v0.1.0")
    logger.info("=" * 70)
    logger.info(f"Industry: {args.industry}")
    logger.info(f"Region: {args.region}")
    logger.info(f"Organization Size: {args.org_size}")
    if args.threat:
        logger.info(f"Threat Scenario: {args.threat}")
    logger.info(f"LLM: provider={args.provider or 'env/config'}  weight={args.weight or 'env/config'}")
    search_label = "disabled" if (args.no_web_search or args.search_provider == "null") \
        else (args.search_provider or "env/config")
    logger.info(f"Search: {search_label}")
    logger.info("=" * 70)

    try:
        # Import here to allow --help to work without all dependencies
        global AttackFlowGenerator
        if AttackFlowGenerator is None:
            from attack_flow_generator import AttackFlowGenerator

        # Initialize generator — credential validation happens inside oic_llm at call time
        generator = AttackFlowGenerator(
            provider=args.provider,
            weight=args.weight,
            search_provider=args.search_provider if args.search_provider != "null" else None,
        )

        # --search-provider null or --no-web-search both disable live search
        include_search = not args.no_web_search and args.search_provider != "null"

        # Generate attack flow
        flow_data = generator.generate_flow(
            industry=args.industry,
            region=args.region,
            organization_size=args.org_size,
            threat_scenario=args.threat,
            include_web_search=include_search,
        )

        # Generate filename (without extension - save_to_file will add appropriate one)
        filename_base = AttackFlowFormatter.generate_filename(
            args.industry, args.region, args.org_size, suffix=""
        )

        saved_files = []

        # Debug: Log the flow format being used
        logger.info("Flow format detected: STIX (.json)")

        # Save in requested formats
        if args.format in ("stix", "json", "both"):
            json_path = AttackFlowFormatter.save_to_file(
                flow_data,
                args.output / filename_base,
                format="stix"
            )
            saved_files.append(json_path)
            logger.info(f"STIX bundle saved: {json_path}")

        if args.format in ("md", "markdown", "both"):
            md_path = AttackFlowFormatter.save_to_file(
                flow_data,
                args.output / filename_base,
                format="md"
            )
            saved_files.append(md_path)
            logger.info(f"Markdown saved: {md_path}")

        # Bundle the self-contained Mermaid viewer with the output directory
        viewer_src = Path(__file__).parent / "attack_flow_viewer.html"
        if viewer_src.exists():
            viewer_dst = args.output / "attack_flow_viewer.html"
            try:
                import shutil
                shutil.copy2(viewer_src, viewer_dst)
                saved_files.append(viewer_dst)
                logger.info(f"Viewer copied: {viewer_dst}")
            except Exception as e:
                logger.warning(f"Could not copy viewer: {e}")
        else:
            logger.warning(f"Viewer not found at {viewer_src}")

        # Print summary to console
        print("\n" + "=" * 70)
        print("ATTACK FLOW GENERATED SUCCESSFULLY")
        print("=" * 70)
        print(AttackFlowFormatter.to_summary_markdown(flow_data))
        print("=" * 70)
        print(f"\nFiles saved to:")
        for f in saved_files:
            print(f"  - {f}")

        print("\nView: open attack_flow_viewer.html and load the generated .json file.")

        return 0

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Error generating attack flow: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def _check_environment() -> bool:
    """Check that the environment has at least one usable LLM credential.

    Does NOT hard-fail on a missing key for a specific provider — oic_llm raises
    a typed ProviderError(kind='auth') at call time for the *selected* provider.
    A missing key for a non-selected provider is irrelevant and ignored.
    """
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
        # Warn only — oic_llm will surface the precise ProviderError at call time.

    has_search = any([
        os.environ.get("TAVILY_API_KEY"),
        os.environ.get("BRAVE_SEARCH_API_KEY"),
    ])
    if not has_search:
        print("Note: No search API key found (TAVILY_API_KEY / BRAVE_SEARCH_API_KEY).")
        print("Web search grounding will be skipped; use --no-web-search to silence this.")

    # Check if corpus is available
    corpus_dir = Path(__file__).parent.parent.parent / "app" / "corpus" / "ref_pillars"
    if not corpus_dir.exists():
        print(f"Warning: Corpus directory not found at {corpus_dir}")
        print("Threat intelligence grounding may be limited.")

    return True  # Always proceed — let oic_llm raise precise errors at call time


if __name__ == "__main__":
    sys.exit(main())
