"""Document loaders: chunking by format and validation. Don't need Ollama or the network."""
from pathlib import Path

from rag import loaders
from rag.loaders import analyze, hash_documents


def write(folder: Path, name: str, content: str | bytes) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def test_md_one_chunk_per_section_and_keeps_the_text_before_it(tmp_path):
    write(tmp_path, "shipping.md", "# Shipping\n\nIntro text.\n\n## Timing\nBetween 2 and 5 days.\n\n## Costs\nFree from $50.\n")
    report = analyze(tmp_path)
    assert not report.errors and not report.warnings
    assert [c["section"] for c in report.chunks] == ["Introduction", "Timing", "Costs"]
    assert report.chunks[0]["text"] == "Shipping\nIntro text."
    assert report.chunks[1]["text"] == "Shipping\n## Timing\nBetween 2 and 5 days."


def test_md_without_sections_is_chunked_by_size_and_warns(tmp_path, monkeypatch):
    monkeypatch.setattr(loaders, "MAX_CHARS", 100)
    monkeypatch.setattr(loaders, "OVERLAP_CHARS", 0)
    write(tmp_path, "note.md", "# Note\n\n" + "\n\n".join(f"Paragraph number {i} with some text." for i in range(10)))
    report = analyze(tmp_path)
    assert len(report.chunks) > 1
    assert all(len(c["text"]) <= 100 + len("Note\n") for c in report.chunks)
    assert any("has no" in w for w in report.warnings)


def test_md_does_not_split_sections_inside_code_blocks(tmp_path):
    write(tmp_path, "a.md", "# A\n\n## One\n```\n## not a section\n```\n\n## Two\ntext\n")
    assert [c["section"] for c in analyze(tmp_path).chunks] == ["One", "Two"]


def test_h3_is_not_a_section_boundary(tmp_path):
    # A real, current limitation (not a design goal): only "## " opens a section. A "### " stays
    # as plain text inside its "## " section's body, same as any other paragraph.
    write(tmp_path, "a.md", "# A\n\n## One\n### Sub\ntext under sub\n\n## Two\nmore text\n")
    report = analyze(tmp_path)
    assert [c["section"] for c in report.chunks] == ["One", "Two"]
    assert "### Sub" in report.chunks[0]["text"]


def test_long_section_is_split_with_overlap(tmp_path, monkeypatch):
    monkeypatch.setattr(loaders, "MAX_CHARS", 200)
    monkeypatch.setattr(loaders, "OVERLAP_CHARS", 40)
    body = "\n\n".join(f"Filler sentence number {i}, long enough to take up space." for i in range(12))
    write(tmp_path, "l.md", f"# L\n\n## Long\n{body}\n")
    chunks = analyze(tmp_path).chunks
    assert len(chunks) > 2
    assert {c["section"] for c in chunks} == {"Long"}
    assert all(c["text"].startswith("L\n## Long\n") for c in chunks)


def test_non_utf8_is_an_error(tmp_path):
    # Needs a non-ASCII character: plain ASCII text encodes the same in latin-1 and UTF-8, so it
    # wouldn't actually trigger the decode error this test is checking for.
    write(tmp_path, "bad.md", "Café shipping".encode("latin-1"))
    assert any("bad.md: not UTF-8" in e for e in analyze(tmp_path).errors)


def test_file_too_big_is_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(loaders, "MAX_FILE_BYTES", 100)
    write(tmp_path, "big.md", "x" * 500)
    assert any("big.md: bigger than" in e for e in analyze(tmp_path).errors)


def test_unsupported_format_is_ignored_with_a_warning_and_hidden_files_dont_count(tmp_path):
    write(tmp_path, "ok.md", "# Ok\n\n## A\ntext\n")
    write(tmp_path, "manual.pdf", b"%PDF-1.4")
    write(tmp_path, ".manifest.json", "{}")
    report = analyze(tmp_path)
    assert not report.errors
    assert report.ignored == ["manual.pdf"]
    assert any("manual.pdf" in w and "unsupported" in w for w in report.warnings)


def test_readme_files_are_not_documents_and_dont_warn(tmp_path):
    write(tmp_path, "README.md", "# How to use this\n\n## Step\nexplanation for humans\n")
    write(tmp_path, "md/shipping.md", "# S\n\n## A\ntext\n")
    report = analyze(tmp_path)
    assert [c["source"] for c in report.chunks] == ["md/shipping.md"]
    assert not report.warnings and not report.errors and not report.ignored


def test_folder_without_documents_is_an_error(tmp_path):
    assert analyze(tmp_path).errors


def test_subfolders_and_fingerprint(tmp_path):
    write(tmp_path, "faq/shipping.md", "# S\n\n## A\ntext\n")
    report = analyze(tmp_path)
    assert report.chunks[0]["source"] == "faq/shipping.md"
    before = hash_documents(tmp_path, report.documents)
    write(tmp_path, "faq/shipping.md", "# S\n\n## A\nchanged text\n")
    assert hash_documents(tmp_path, analyze(tmp_path).documents) != before
