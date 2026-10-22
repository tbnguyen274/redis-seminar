"""Store per-run results and present JSON, CSV and console summaries."""

import csv
import json
import tempfile
import time
from pathlib import Path

import constants as settings

SUMMARY_FIELDS = [
    "trial", "mode", "delay_seconds", "expected_dbsize_before",
    "verified_correct_after", "missing_keys", "corrupt_keys",
    "ack_to_kill_seconds",
]


def create_run_dir(base):
    """Create a unique directory, even for runs in the same second."""
    root = base / "results"
    root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%SZ", time.gmtime())
    return Path(tempfile.mkdtemp(prefix=f"run-{stamp}-", dir=root))


def folder_bytes(folder):
    if not folder.exists():
        return 0
    return sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def write_json(path, payload):
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def write_summary(rows, run_root):
    output = run_root / "summary.csv"
    output.parent.mkdir(exist_ok=True)
    fields = SUMMARY_FIELDS + (
        ["delta_fsync_status"] if any(r.get("fsync_tracing") for r in rows)
        else []
    )
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    return output


def print_section(title):
    """Separate console sections with portable ASCII characters."""
    print(f"\n{title}")
    print("-" * max(settings.CONSOLE_SECTION_WIDTH, len(title)))


def print_field(label, value):
    """Align short labels without padding long filesystem paths."""
    print(f"  {label:<{settings.CONSOLE_LABEL_WIDTH}} : {value}")


def print_path(label, path):
    """Keep long artifact paths on their own lines for easy copying."""
    print(f"  {label}:\n    {path}")


def save_trial_results(run_dir, trial, rows):
    write_json(run_dir / "trial-results.json", rows)
    traced = any(row.get("fsync_tracing") for row in rows)
    headers = [
        "Mode", "Delay(s)", "Expected", "Correct", "Missing", "Corrupt",
        "ACK(ms)",
    ]
    if traced:
        headers.append("Fsync")
    display_rows = []
    for row in rows:
        ack_ms = row['ack_to_kill_seconds'] * settings.MILLISECONDS_PER_SECOND
        cells = [
            row["mode"].upper(),
            f"{row['delay_seconds']:g}",
            str(row["expected_dbsize_before"]),
            str(row["verified_correct_after"]),
            str(row["missing_keys"]),
            str(row["corrupt_keys"]),
            f"{ack_ms:.{settings.MILLISECONDS_DECIMAL_PLACES}f}",
        ]
        if traced:
            cells.append(row.get("delta_fsync_status", "Unknown"))
        display_rows.append(cells)
    widths = [
        max(len(value) for value in column)
        for column in zip(headers, *display_rows)
    ]
    print_section(f"Trial {trial}: recovery results")
    print(" | ".join(
        label.ljust(width) for label, width in zip(headers, widths)
    ))
    print("-+-".join("-" * width for width in widths))
    for cells in display_rows:
        print(" | ".join(
            value.ljust(width) if label in ("Mode", "Fsync")
            else value.rjust(width)
            for label, value, width in zip(headers, cells, widths)
        ))
    print()
    print_field("Delay(s)", "Requested wait after both delta batches ACK")
    print_field("Expected", "SETs acknowledged before crash")
    print_field("Correct", "Keys recovered with the expected value")
    print_field("Missing", "Keys absent after restart")
    print_field("Corrupt", "Keys recovered with an unexpected value")
    print_field("ACK(ms)", "Final SET ACK -> SIGKILL (measured)")
    if traced:
        print_field("Fsync", "Delta sync confirmed before crash; N/A = RDB")
        print_field("Trace note", "OS-level confirmation; adds overhead")
    print_path("Trial files", run_dir)
