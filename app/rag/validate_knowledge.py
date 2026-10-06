"""Validates the documents BEFORE indexing. Exits with code 1 if there are errors.

    python -m rag.validate_knowledge [folder]      (default: DOCS_DIR or knowledge/)

Run by the pipeline against the S3 copy: if something is wrong, nothing gets indexed or deployed,
and production keeps running the last good version. Never prints the documents' content.
"""
import os
import sys
from collections import Counter
from pathlib import Path

from rag.loaders import analyze, hash_documents


def main() -> int:
    folder = Path(sys.argv[1] if len(sys.argv) > 1 else os.getenv("DOCS_DIR", "knowledge"))
    report = analyze(folder)
    in_actions = os.getenv("GITHUB_ACTIONS") == "true"

    for warning in report.warnings:
        print(f"::warning::{warning}" if in_actions else f"WARNING: {warning}")
    for error in report.errors:
        print(f"::error::{error}" if in_actions else f"ERROR: {error}")

    formats = Counter(p.suffix.lower() for p in report.documents)
    summary = ", ".join(f"{n} {f}" for f, n in sorted(formats.items())) or "none"
    print(f"Documents: {len(report.documents)} ({summary}) · chunks: {len(report.chunks)} · ignored: {len(report.ignored)}")
    if report.documents:
        print(f"Fingerprint: {hash_documents(folder, report.documents)}")

    if report.errors:
        print(f"Rejected: {len(report.errors)} error(s). Fix the files and upload them again.")
        return 1
    print("Documents are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
