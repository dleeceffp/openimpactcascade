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
  # Generate attack flow for healthcare in US (medium enterprise)
  python cli.py --industry healthcare --region "United States" --org-size "500-1000"

  # Generate with specific threat scenario
  python cli.py --industry financial --region Canada --org-size SME \\
      --threat "ransomware via phishing"

  # Output to specific directory with markdown summary
  python cli.py --industry manufacturing --region UK --org-size Enterprise \\
      --output ./my_flows --format both
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
        choices=["json", "md", "markdown", "both"],
        default="both",
        help="Output format (default: both)"
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
    logger.info("=" * 70)

    try:
        # Import here to allow --help to work without all dependencies
        global AttackFlowGenerator
        if AttackFlowGenerator is None:
            from attack_flow_generator import AttackFlowGenerator

        # Initialize generator
        generator = AttackFlowGenerator()

        # Generate attack flow
        flow_data = generator.generate_flow(
            industry=args.industry,
            region=args.region,
            organization_size=args.org_size,
            threat_scenario=args.threat,
            include_web_search=not args.no_web_search
        )

        # Generate filename
        filename_base = AttackFlowFormatter.generate_filename(
            args.industry, args.region, args.org_size
        )

        saved_files = []

        # Save in requested formats
        if args.format in ("json", "both"):
            json_path = AttackFlowFormatter.save_to_file(
                flow_data,
                args.output / f"{filename_base}.json",
                format="json"
            )
            saved_files.append(json_path)
            logger.info(f"JSON saved: {json_path}")

        if args.format in ("md", "markdown", "both"):
            md_path = AttackFlowFormatter.save_to_file(
                flow_data,
                args.output / f"{filename_base}.md",
                format="md"
            )
            saved_files.append(md_path)
            logger.info(f"Markdown saved: {md_path}")

        # Print summary to console
        print("\n" + "=" * 70)
        print("ATTACK FLOW GENERATED SUCCESSFULLY")
        print("=" * 70)
        print(AttackFlowFormatter.to_summary_markdown(flow_data))
        print("=" * 70)
        print(f"\nFiles saved to:")
        for f in saved_files:
            print(f"  - {f}")

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
    """Check that required environment is configured."""
    import os

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY='your-api-key'")
        return False

    # Check if corpus is available
    corpus_dir = Path(__file__).parent.parent.parent / "app" / "corpus" / "ref_pillars"
    if not corpus_dir.exists():
        print(f"Warning: Corpus directory not found at {corpus_dir}")
        print("Threat intelligence grounding may be limited.")

    return True


if __name__ == "__main__":
    sys.exit(main())
