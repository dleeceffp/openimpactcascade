# Test Fixtures — Pillar Reference Data

## Status: TRANSITORY / SAFE TO DELETE

**All files in this directory and subdirectories are transitory test fixtures.**
They are copies of production pillar YAML files used solely for CI acceptance
testing. They may be deleted, overwritten, or refreshed at any time without
impacting production data.

## Source of Truth

Production pillar files live in:
```
app/corpus/ref_pillars/
├── breach_reports/     # DBIR likelihood data (Verizon)
├── financial/           # NetDiligence & IBM cost data
└── threat_landscape/     # Future threat intel
```

## How to Refresh Fixtures

Copy current production files to this directory for testing:

```bash
# From repo root
cp app/corpus/ref_pillars/breach_reports/dbir-likelihood-by-industry.2025.yaml \
   tests/fixtures/pillars/breach_reports/
   
cp app/corpus/ref_pillars/financial/netdiligence-cyber-claims.2025.yaml \
   tests/fixtures/pillars/financial/
   
cp app/corpus/ref_pillars/financial/ibm-cost-by-industry.2025.yaml \
   tests/fixtures/pillars/financial/
```

## Fixture Organization

```
tests/fixtures/pillars/
├── breach_reports/          # DBIR likelihood fixtures
│   └── dbir-likelihood-by-industry.2025.yaml
├── financial/                # Magnitude fixtures
│   ├── netdiligence-cyber-claims.2025.yaml
│   └── ibm-cost-by-industry.2025.yaml
├── threat_landscape/        # Reserved for future pillars
└── test_readme.md           # This file
```

## Why Separate Fixtures?

Tests must run against **known, stable** data to avoid false negatives when
production files change. The acceptance tests verify:
- Crosswalk resolution against real keys
- Edition selection (latest wins)
- Field pass-through (no transformation)
- Honesty guards (no derived probability fields)

Using production files directly would create a coupling between data updates and
test breakage — the fixture layer isolates this.

## Running the Tests

The acceptance tests live at `tests/test_pillar_reader.py`. Run them from the repo root:

```bash
# Run all pillar reader acceptance tests
python -m pytest tests/test_pillar_reader.py -v

# Run with coverage report (shows crosswalk resolution for all industries)
python -m pytest tests/test_pillar_reader.py::test_coverage_report_all_canonicals -v -s

# Quick coverage report without pytest (standalone)
python -c "
import sys
sys.path.insert(0, 'app')
from corpus.pillar_reader import PillarReader
r = PillarReader(pillars_dir='tests/fixtures/pillars', enabled=True)
r.load()
report = r.coverage_report()
for canonical, info in sorted(report.items()):
    status = 'OK' if info['in_latest'] else 'MISS'
    print(f'{status:4s} {canonical:35s} -> {info[\"resolved_key\"]!r}')
"
```

**Critical tests to watch:**
- `test_real_estate_uses_dedicated_dbir_row` — validates `real estate` → `real_estate` (not construction)
- `test_technology_resolves_to_information` — validates many-canonical → one-key mapping
- `test_coverage_report_all_canonicals` — full crosswalk integrity check

## Adding New Test Scenarios

1. Copy the relevant YAML file to the appropriate subdirectory
2. Reference it in `test_pillar_reader.py` acceptance tests
3. Document the specific industry/series being tested in the test docstring

## Cleanup Policy

- Fixtures older than the current production edition may be deleted
- Multiple editions (2024, 2025) may coexist for trend-testing
- If a fixture becomes orphaned (no tests reference it), delete it
