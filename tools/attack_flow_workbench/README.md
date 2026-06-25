# MITRE Attack Flow Generation Workbench

A standalone prototype application for generating MITRE Attack Flows based on industry, region, and organization size. This tool uses the same corpus and MITRE schemas as the main OIC application to ensure consistency.

## Overview

The Attack Flow Workbench generates realistic, industry-specific cyber attack scenarios formatted according to the [MITRE Attack Flow specification](https://github.com/center-for-threat-informed-defense/attack-flow). It combines:

- **Threat Intelligence Grounding**: Uses the same Verizon DBIR corpus as the main OIC app
- **MITRE ATT&CK Integration**: Leverages the enterprise-attack-19.1.json matrix for technique IDs
- **LLM-Powered Generation**: Uses Claude to create realistic attack scenarios
- **Web Search**: Optionally enriches with recent threat intelligence

## Installation

1. Ensure you're in the OIC_SBX project directory
2. Install dependencies (if not already installed):
   ```bash
   pip install anthropic pyyaml requests
   ```

3. Set required environment variables:
   ```bash
   export ANTHROPIC_API_KEY="your-anthropic-api-key"
   export GOOGLE_SEARCH_API_KEY="your-google-api-key"  # Optional, for web search
   export GOOGLE_SEARCH_CSE_ID="your-cse-id"           # Optional, for web search
   ```

## Usage

### Basic Usage

Generate an attack flow for a specific industry/region:

```bash
cd tools/attack_flow_workbench
python cli.py --industry healthcare --region "United States" --org-size "500-1000"
```

### With Specific Threat Scenario

```bash
python cli.py --industry financial --region Canada --org-size SME \
    --threat "ransomware via business email compromise"
```

### Output Options

```bash
# Generate only JSON output
python cli.py -i manufacturing -r UK -s Enterprise --format json

# Generate only Markdown summary
python cli.py -i retail -r "North America" -s SME --format md

# Custom output directory
python cli.py -i technology -r "Europe" -s Enterprise -o ./my_flows

# Disable web search (use only corpus grounding)
python cli.py -i energy -r "United States" -s "Large Enterprise" --no-web-search
```

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--industry` | `-i` | Industry sector (required) |
| `--region` | `-r` | Region/country (required) |
| `--org-size` | `-s` | Organization size (required) |
| `--threat` | `-t` | Specific threat scenario (optional) |
| `--output` | `-o` | Output directory (default: `generated/attack_flows`) |
| `--format` | `-f` | Output format: `json`, `md`, `markdown`, or `both` |
| `--no-web-search` | | Disable web search for threat intelligence |
| `--verbose` | `-v` | Enable verbose logging |
| `--version` | | Show version and exit |

## Output Format

The tool generates two types of output:

### 1. JSON (MITRE Attack Flow)

A valid MITRE Attack Flow bundle conforming to the [Attack Flow Schema 2.0.0](https://center-for-threat-informed-defense.github.io/attack-flow/schema/attack-flow-schema-2.0.0.json):

```json
{
  "type": "bundle",
  "id": "bundle--uuid",
  "objects": [
    {
      "type": "attack-flow",
      "id": "attack-flow--uuid",
      "name": "Attack Flow - Healthcare Ransomware",
      "scope": "incident",
      "start_refs": ["attack-action--uuid"],
      "x_oic_context": {
        "industry": "healthcare",
        "region": "United States",
        "organization_size": "500-1000",
        "generated_at": "2025-01-15T10:30:00"
      }
    },
    {
      "type": "attack-action",
      "id": "attack-action--uuid",
      "name": "Spearphishing Attachment",
      "technique_id": "T1566.001",
      "tactic_id": "initial-access"
    }
  ]
}
```

### 2. Markdown Summary

A human-readable summary with:
- Attack context (industry, region, org size)
- Step-by-step attack chain with MITRE techniques
- Targeted assets

## Architecture

```
attack_flow_workbench/
├── __init__.py              # Package initialization
├── cli.py                   # CLI entry point
├── config.py                # Configuration settings
├── mitre_loader.py          # MITRE ATT&CK matrix loader
├── corpus_grounding.py      # Threat intel from DBIR corpus
├── web_search.py            # Google Custom Search integration
├── attack_flow_generator.py # Main generation logic
├── formatter.py             # Output formatters
└── README.md                # This file
```

### Key Components

- **MitreTechniqueLookup**: Loads and indexes MITRE ATT&CK techniques from the same JSON files used by the main OIC app
- **ThreatIntelGrounding**: Reuses the pillar reader from `app/corpus/` for DBIR threat intelligence
- **AttackFlowGenerator**: Orchestrates LLM-based attack flow generation with proper grounding
- **AttackFlowFormatter**: Converts to MITRE Attack Flow format and generates summaries

## Consistency with Main OIC App

This workbench ensures consistency with the main OIC application by:

1. **Same Corpus**: Uses `app/corpus/ref_pillars/` for threat intelligence
2. **Same MITRE Schemas**: Uses `refdocs/matrices/enterprise-attack-19.1.json`
3. **Same Input Parameters**: Industry, region, and organization size
4. **Same Grounding Logic**: Leverages `pillar_reader.py` and `pillar_crosswalk.py`

## Integration with Attack Flow Builder

The generated `.json` files can be imported into the [MITRE Attack Flow Builder](https://center-for-threat-informed-defense.github.io/attack-flow/) for visualization and editing.

## Development

### Running Tests

```bash
cd tools/attack_flow_workbench
python -m pytest  # If tests are added
```

### Extending the Workbench

To add new attack patterns:
1. Update `attack_flow_generator.py` with new pattern mappings
2. Add technique lookups to `mitre_loader.py`

## License

Part of the OIC (Operational Intelligence for Cybersecurity) project.
