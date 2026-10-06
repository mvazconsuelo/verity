"""Reads and chunks the business documents: .md only.

Splits by '## ' sections (with the '# ' title in front) and produces a list of chunks
{"source", "section", "text"} ready to compute vectors. The text before the first '##' is kept;
a document without '##' is chunked by size. Only uses the standard library, so the validator can
run anywhere without installing anything.

Sections or blocks longer than CHUNK_MAX_CHARS are split, with a bit of overlap.

Kept deliberately as a single function: a generic Parser/Document/Chunker split (to support other
formats like HTML or PDF) was built and removed — there was no real document in another format to
justify it, and it added a layer of indirection for a capability nobody used. If that need ever
comes back for real, build it again then, against the actual format in hand.
"""
import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

FORMATS = {".md"}

MAX_CHARS = int(os.getenv("CHUNK_MAX_CHARS", "1200"))
OVERLAP_CHARS = int(os.getenv("CHUNK_OVERLAP_CHARS", "150"))
MAX_FILE_BYTES = int(os.getenv("MAX_FILE_KB", "512")) * 1024
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "2000"))


@dataclass
class Report:
    """Result of analyzing a folder of documents."""

    documents: list[Path] = field(default_factory=list)  # the ones that go into the index
    chunks: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)  # don't block publishing
    errors: list[str] = field(default_factory=list)  # block publishing
    ignored: list[str] = field(default_factory=list)  # unsupported format


def list_files(folder: Path) -> tuple[list[Path], list[Path]]:
    """(accepted, ignored), sorted. Hidden files/folders (.something) and README files
    (README.md, README.txt...) don't count: they're explanations for people, not business documents."""
    all_files = sorted(
        p for p in folder.rglob("*")
        if p.is_file()
        and not any(part.startswith(".") for part in p.relative_to(folder).parts)
        and p.stem.lower() != "readme"
    )
    return [p for p in all_files if p.suffix.lower() in FORMATS], [p for p in all_files if p.suffix.lower() not in FORMATS]


def _split(text: str, max_chars: int, overlap: int) -> list[str]:
    """Splits a long text into pieces of at most max_chars, cutting at paragraphs and, if needed, at words."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    units = []
    for paragraph in re.split(r"\n\s*\n", text):
        p = paragraph.strip()
        while len(p) > max_chars:  # a giant paragraph gets cut at a word
            cut = p.rfind(" ", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            units.append(p[:cut].strip())
            p = p[cut:].strip()
        if p:
            units.append(p)

    pieces, current = [], ""
    for u in units:
        if current and len(current) + 2 + len(u) > max_chars:
            pieces.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            tail = tail[tail.find(" ") + 1:] if " " in tail else ""  # the overlap starts at a whole word
            current = f"{tail} {u}".strip() if tail else u
            if len(current) > max_chars:  # doesn't fit with the overlap: no overlap
                current = u
        else:
            current = f"{current}\n\n{u}" if current else u
    if current:
        pieces.append(current)
    return pieces


def chunk_md(text: str, source: str) -> list[dict]:
    lines = text.replace("\r\n", "\n").strip().splitlines()
    title = Path(source).stem
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]
    rest = "\n".join(lines)

    chunks = []
    # A '## ' only opens a section outside of code blocks
    blocks, current, in_code = [], [], False
    for line in rest.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if line.startswith("## ") and not in_code:
            blocks.append(current)
            current = []
        current.append(line)
    blocks.append(current)

    for i, block in enumerate(blocks):
        if i == 0:  # whatever is before the first '##'
            section, body, heading = "Introduction", "\n".join(block), ""
        else:
            section = block[0][3:].strip()
            body, heading = "\n".join(block[1:]), f"## {section}\n"
        for piece in _split(body, MAX_CHARS, OVERLAP_CHARS):
            chunks.append({"source": source, "section": section, "text": f"{title}\n{heading}{piece}"})
        if i > 0 and not body.strip():  # section with only a title: the title is kept
            chunks.append({"source": source, "section": section, "text": f"{title}\n{heading}".strip()})
    return chunks


def _read(path: Path) -> str:
    """UTF-8, with or without a BOM mark (some editors add one)."""
    return path.read_bytes().decode("utf-8-sig")


def analyze(folder: Path) -> Report:
    """Reads the whole folder and says what goes into the index, what's ignored and what's wrong. Prints nothing."""
    report = Report()
    accepted, ignored = list_files(folder)
    report.ignored = [p.relative_to(folder).as_posix() for p in ignored]
    report.warnings += [f"{n}: unsupported format, ignored (.md only)" for n in report.ignored]

    for path in accepted:
        name = path.relative_to(folder).as_posix()
        if path.stat().st_size > MAX_FILE_BYTES:
            report.errors.append(f"{name}: bigger than {MAX_FILE_BYTES // 1024} KB")
            continue
        try:
            text = _read(path)
        except UnicodeDecodeError:
            report.errors.append(f"{name}: not UTF-8 (save it as UTF-8)")
            continue
        if "\x00" in text:
            report.errors.append(f"{name}: contains null characters (is it a binary file with the wrong extension?)")
            continue
        if not text.strip():
            report.errors.append(f"{name}: is empty")
            continue

        if not any(line.startswith("# ") for line in text.splitlines()[:1]):
            report.warnings.append(f"{name}: doesn't start with a '# ' title (the file name will be used instead)")
        if "\n## " not in "\n" + text:
            report.warnings.append(f"{name}: has no '## ' sections (chunked by size, and retrieval works worse)")
        chunks = chunk_md(text, name)

        if not chunks:
            report.errors.append(f"{name}: produced no text chunk")
            continue
        report.documents.append(path)
        report.chunks += chunks

    if not report.documents and not report.errors:
        report.errors.append(f"no .md document found in {folder}")
    if len(report.chunks) > MAX_CHUNKS:
        report.errors.append(f"there are {len(report.chunks)} chunks and the max is {MAX_CHUNKS} (raise MAX_CHUNKS if that's on purpose)")
    return report


def hash_documents(folder: Path, documents: list[Path]) -> str:
    """Fingerprint of the documents (paths and content): says which version of the documentation the index was built from."""
    h = hashlib.sha256()
    for path in documents:
        h.update(path.relative_to(folder).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:12]
