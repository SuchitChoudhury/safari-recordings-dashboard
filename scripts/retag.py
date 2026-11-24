"""Re-apply tags and the primary domain without changing other recording fields."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tagging import DATA_FILE, assign_domains, assign_tags

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--file", type=Path, default=DATA_FILE)
args = parser.parse_args()

if not args.file.exists():
    print(f"no data file at {args.file}")
    sys.exit(1)

entries = json.loads(args.file.read_text(encoding="utf-8"))
changed = 0
for e in entries:
    tags = assign_tags(e.get("event", ""))
    domains = assign_domains(tags, e.get("event", ""))
    if tags != e.get("tags") or domains != e.get("domains"):
        e["tags"] = tags
        e["domains"] = domains
        changed += 1

args.file.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"retagged {changed} of {len(entries)} entries")
