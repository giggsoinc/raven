# Stack Rules

## Approved (never flag)
Stdlib: os sys json logging typing datetime pathlib re collections
itertools functools abc dataclasses asyncio contextlib io math
random hashlib uuid copy enum time threading subprocess argparse

## Check against manifest stack.libraries + stack.data
Run: python3 .claude/scripts/cve-check.py --library {lib} --version {ver}

## Decisions
- Exit 0 → auto-approved
- Exit 1 → hard block (critical CVE)
- Exit 2 → approval flow (moderate CVE)
- Exit 3 → approval flow (unknown, clean)

## Pandas rule
import pandas → advise: "Manifest prefers polars. Switch or get approval."
