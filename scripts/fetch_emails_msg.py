"""
fetch_emails_msg.py
-------------------
Ingestion from a folder of .msg files (Outlook MSG format) using extract-msg.
Fast, no COM, no auth, no admin consent. Ideal when you've dumped the folder
contents to disk.

Usage::

    python fetch_emails_msg.py                    # default dump dir, merge into existing data
    python fetch_emails_msg.py --no-merge         # discard data.json and rebuild from dump
    python fetch_emails_msg.py --dir <path>       # custom dump directory
"""
from __future__ import annotations

import argparse
import email
import json
import sys
from datetime import datetime, timezone
from email import policy
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

import extract_msg

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tagging import (
    DATA_DIR,
    DATA_FILE,
    STATE_FILE,
    assign_domains,
    assign_tags,
    extract_recording_link,
    matches_subject,
    normalize_key,
    parse_event_and_presenter,
)


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


DEFAULT_DUMP_DIR = DATA_DIR.parent / "dump"


def to_iso_date(dt) -> str:
    """Return UTC date as 'YYYY-MM-DD'. Empty string if no date."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt[:10]
    try:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return str(dt)[:10]


def load_existing() -> tuple[list[dict], dict]:
    entries: list[dict] = []
    state: dict = {}
    if DATA_FILE.exists():
        try:
            entries = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            if not isinstance(entries, list):
                entries = []
        except Exception as e:
            log(f"warning: failed to read data.json ({e}); starting empty")
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    return entries, state


def write_outputs(by_key: dict[str, dict], last_iso: str) -> None:
    entries_sorted = sorted(by_key.values(), key=lambda e: e["received"], reverse=True)
    DATA_FILE.write_text(json.dumps(entries_sorted, indent=2, ensure_ascii=False), encoding="utf-8")
    STATE_FILE.write_text(
        json.dumps(
            {
                "last_run_iso": last_iso,
                "last_run_at": datetime.now(timezone.utc).isoformat(),
                "total_entries": len(entries_sorted),
                "source": "msg-dump",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def merge_entry(by_key: dict[str, dict], entry: dict) -> None:
    key = entry["dedup_key"]
    existing = by_key.get(key)
    if existing is None or entry["received"] > existing["received"]:
        by_key[key] = entry


def _build_entry(subject: str, sender: str, received_date: str, html: str, source_file: str) -> tuple[dict | None, str]:
    if not matches_subject(subject):
        return None, "subject-mismatch"
    event, presenter = parse_event_and_presenter(subject)
    if not event:
        return None, "parse-fail"
    link = extract_recording_link(html)
    if not link:
        return None, "no-link"
    tags = assign_tags(event)
    return {
        "event": event,
        "presenter": presenter,
        "received": received_date,
        "domains": assign_domains(tags),
        "tags": tags,
        "sender": sender,
        "subject": subject,
        "source_file": source_file,
        "dedup_key": normalize_key(event, presenter),
    }, "kept"


def process_msg(path: Path) -> tuple[dict | None, str]:
    """Process a .msg (Outlook MSG) file via extract-msg."""
    try:
        m = extract_msg.openMsg(str(path))
    except Exception as e:
        log(f"  open fail: {path.name}: {e}")
        return None, "open-fail"
    try:
        subject = (m.subject or "").strip()
    except Exception:
        subject = ""
    if not matches_subject(subject):
        try:
            m.close()
        except Exception:
            pass
        return None, "subject-mismatch"

    received_date = to_iso_date(getattr(m, "date", None))
    try:
        sender = m.sender or ""
    except Exception:
        sender = ""

    html = ""
    try:
        b = m.htmlBody
        if isinstance(b, bytes):
            try:
                html = b.decode("utf-8", errors="replace")
            except Exception:
                html = b.decode("latin-1", errors="replace")
        elif isinstance(b, str):
            html = b
    except Exception:
        html = ""
    if not html:
        try:
            html = m.body or ""
        except Exception:
            html = ""

    try:
        m.close()
    except Exception:
        pass

    return _build_entry(subject, sender, received_date, html, path.name)


def process_eml(path: Path) -> tuple[dict | None, str]:
    """Process a .eml (RFC 822) file via the standard library."""
    try:
        with open(path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
    except Exception as e:
        log(f"  open fail: {path.name}: {e}")
        return None, "open-fail"

    subject = (msg.get("Subject") or "").strip()
    if not matches_subject(subject):
        return None, "subject-mismatch"

    # Sender: prefer the email address.
    sender = ""
    try:
        addrs = getaddresses([msg.get("From") or ""])
        if addrs and addrs[0][1]:
            sender = addrs[0][1]
    except Exception:
        pass

    # Date.
    received_date = ""
    date_hdr = msg.get("Date")
    if date_hdr:
        try:
            dt = parsedate_to_datetime(date_hdr)
            received_date = to_iso_date(dt)
        except Exception:
            pass

    # Body — prefer text/html.
    html = ""
    plain = ""
    try:
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html" and not html:
                try:
                    html = part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    cs = part.get_content_charset() or "utf-8"
                    try:
                        html = payload.decode(cs, errors="replace")
                    except Exception:
                        html = payload.decode("latin-1", errors="replace")
            elif ctype == "text/plain" and not plain:
                try:
                    plain = part.get_content()
                except Exception:
                    payload = part.get_payload(decode=True) or b""
                    cs = part.get_content_charset() or "utf-8"
                    try:
                        plain = payload.decode(cs, errors="replace")
                    except Exception:
                        plain = payload.decode("latin-1", errors="replace")
    except Exception:
        pass

    return _build_entry(subject, sender, received_date, html or plain, path.name)


def run(dump_dir: Path, full: bool, merge_existing: bool, report_path: Path | None) -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not dump_dir.exists():
        log(f"ERROR: dump dir not found: {dump_dir}")
        return 2

    by_key: dict[str, dict] = {}
    if merge_existing:
        existing, _ = load_existing()
        # also normalise legacy entries' received from ISO datetime to date
        for e in existing:
            r = e.get("received") or ""
            if "T" in r:
                e["received"] = r[:10]
            if "dedup_key" in e:
                by_key[e["dedup_key"]] = e
        log(f"loaded {len(by_key)} existing entries from data.json")

    files = sorted([*dump_dir.rglob("*.msg"), *dump_dir.rglob("*.eml")])
    log(f"found {len(files)} email files (.msg + .eml) in {dump_dir}")
    if not files:
        log("nothing to do")
        return 0

    # outcome[reason] = list[file_name]
    outcome: dict[str, list[str]] = {
        "kept": [],
        "no-link": [],
        "subject-mismatch": [],
        "parse-fail": [],
        "open-fail": [],
    }
    max_received = "1970-01-01"
    for i, path in enumerate(files, 1):
        if i % 50 == 0:
            log(f"  progress: {i}/{len(files)}")
        if path.suffix.lower() == ".eml":
            entry, reason = process_eml(path)
        else:
            entry, reason = process_msg(path)
        outcome[reason].append(path.name)
        if entry is None:
            continue
        merge_entry(by_key, entry)
        if entry["received"] > max_received:
            max_received = entry["received"]

    log("=== per-file outcome ===")
    for reason, names in outcome.items():
        log(f"  {reason:>17}: {len(names)}")
    if outcome["no-link"]:
        log("  files skipped because no recording link was found:")
        for n in outcome["no-link"][:25]:
            log(f"    - {n}")
        if len(outcome["no-link"]) > 25:
            log(f"    ... and {len(outcome['no-link']) - 25} more")
    if outcome["subject-mismatch"]:
        log("  files skipped because subject did not match a recording prefix:")
        for n in outcome["subject-mismatch"][:25]:
            log(f"    - {n}")
        if len(outcome["subject-mismatch"]) > 25:
            log(f"    ... and {len(outcome['subject-mismatch']) - 25} more")
    if outcome["open-fail"]:
        log("  *** files that FAILED TO OPEN — these have not been ingested:")
        for n in outcome["open-fail"]:
            log(f"    - {n}")
    if outcome["parse-fail"]:
        log("  files where event/presenter could not be parsed:")
        for n in outcome["parse-fail"]:
            log(f"    - {n}")

    write_outputs(by_key, max_received)
    log(f"wrote {len(by_key)} unique entries to {DATA_FILE}")
    log(f"state.last_run_iso = {max_received}")

    if report_path:
        report = {
            "summary": {k: len(v) for k, v in outcome.items()},
            "total_files": len(files),
            "unique_entries": len(by_key),
            "details": outcome,
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        log(f"wrote per-file report to {report_path}")

    # Safety: refuse to declare success if any file failed to open or parse —
    # the caller must NOT delete the dump if exit code is non-zero.
    failed = len(outcome["open-fail"]) + len(outcome["parse-fail"])
    if failed:
        log("")
        log(f"!!! {failed} file(s) failed to open/parse. Exiting non-zero.")
        log("    DO NOT delete the dump folder until these are resolved.")
        return 3

    log("")
    log(f"OK — all {len(files)} file(s) processed cleanly. Safe to delete the dump folder.")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(DEFAULT_DUMP_DIR), help=f"folder containing .msg files (default: {DEFAULT_DUMP_DIR})")
    ap.add_argument("--full", action="store_true", help="(no-op for msg mode; always re-reads dump)")
    ap.add_argument("--no-merge", action="store_true", help="discard data.json and start fresh from the dump only")
    ap.add_argument("--report", default=str(DATA_DIR / "ingest_report.json"),
                    help="write a per-file outcome report (json). pass empty string to disable.")
    args = ap.parse_args(argv)
    report_path = Path(args.report) if args.report else None
    try:
        return run(Path(args.dir), args.full, merge_existing=not args.no_merge, report_path=report_path)
    except Exception as e:
        log(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass
    sys.exit(main(sys.argv[1:]))
