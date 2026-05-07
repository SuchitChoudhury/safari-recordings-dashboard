"""Re-apply tagging rules to data.json without touching the dump.
Use after editing TOPIC_RULES or TAG_TO_DOMAINS in tagging.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tagging import DATA_FILE, assign_domains, assign_tags

if not DATA_FILE.exists():
    print(f"no data file at {DATA_FILE}")
    sys.exit(1)

entries = json.loads(DATA_FILE.read_text(encoding="utf-8"))
changed = 0
for e in entries:
    tags = assign_tags(e.get("event", ""))
    domains = assign_domains(tags)
    if tags != e.get("tags") or domains != e.get("domains"):
        e["tags"] = tags
        e["domains"] = domains
        changed += 1
    r = e.get("received") or ""
    if "T" in r:
        e["received"] = r[:10]
    for f in ("recording_url", "outlook_web_link"):
        e.pop(f, None)

DATA_FILE.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
unc = sum(1 for e in entries if e.get("tags") == ["Uncategorized"])
print(f"retagged {changed} of {len(entries)} entries; uncategorized: {unc}")
