#!/usr/bin/env python3
"""
README
======

Purpose:
- Extract annotations/comments from one PDF or a directory of PDFs.
- Export key information in `jsonl`, `csv`, or concise `txt` format.

Quick Start:
- Single file to concise TXT:
    python utils/pdf_comment_extractor.py --input "C:/path/file.pdf" --output "C:/path/out.txt" --format txt --skip-errors
- Directory to JSONL (recursive):
    python utils/pdf_comment_extractor.py --input "C:/pdfs" --output "C:/out/comments.jsonl" --format jsonl --recursive --skip-errors

Important Flags:
- --types highlight,text,freetext   Filter by normalized annotation subtype.
- --skip-errors                     Continue processing when a file/page fails.
- --failure-log <path>              Write failures as JSONL.
- --verbose                         Print per-file processing summary.

TXT Output:
- Always prints:
    Page <n>
    Comment: <text or ->
    Quoted: <text or empty>

Notes:
- `Quoted` text is extracted from annotation quad/rect regions and may be short or partial
    depending on PDF text-layer quality.
- Failure details are saved to `<output>.failures.jsonl` by default.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import fitz  # PyMuPDF


SUBTYPE_MAP = {
    "Highlight": "highlight",
    "Underline": "underline",
    "StrikeOut": "strikeout",
    "Squiggly": "squiggly",
    "Text": "text",
    "FreeText": "freetext",
    "Caret": "caret",
    "Stamp": "stamp",
    "Ink": "ink",
    "Line": "line",
    "Square": "square",
    "Circle": "circle",
    "Polygon": "polygon",
    "PolyLine": "polyline",
    "FileAttachment": "file_attachment",
    "Sound": "sound",
    "Redact": "redact",
    "Popup": "popup",
}


@dataclass
class CommentRecord:
    id: str
    file: str
    page: int
    subtype: str
    author: str
    comment_text: str
    quoted_text: str
    context_text: str
    created_at: str | None
    modified_at: str | None
    bbox: list[float]
    quadpoints: list[list[float]]
    color: list[float]
    extraction_confidence: float
    warnings: list[str]
    raw: dict[str, Any]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract PDF comments and highlighted text.")
    parser.add_argument("--input", required=True, help="PDF file or directory")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument(
        "--format",
        choices=["jsonl", "csv", "txt"],
        default="jsonl",
        help="Output format",
    )
    parser.add_argument("--recursive", action="store_true", help="Recurse for PDFs in directories")
    parser.add_argument(
        "--types",
        default="",
        help="Comma-separated normalized types filter, e.g. highlight,text,freetext",
    )
    parser.add_argument("--skip-errors", action="store_true", help="Continue on file errors")
    parser.add_argument("--verbose", action="store_true", help="Verbose logs")
    parser.add_argument(
        "--context-chars",
        type=int,
        default=220,
        help="Number of context chars around quoted text",
    )
    parser.add_argument(
        "--failure-log",
        default="",
        help="Optional failure log JSONL path. Defaults to <output>.failures.jsonl",
    )
    return parser.parse_args()


def normalize_subtype(subtype: str) -> str:
    return SUBTYPE_MAP.get(subtype or "", (subtype or "unknown").lower())


def parse_pdf_date(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    if text.startswith("D:"):
        text = text[2:]
    match = re.match(
        r"^(\d{4})(\d{2})?(\d{2})?(\d{2})?(\d{2})?(\d{2})?([Zz]|[+-]\d{2}'?\d{2}'?)?$",
        text,
    )
    if not match:
        return None
    year, month, day, hour, minute, second, tz = match.groups()
    month = month or "01"
    day = day or "01"
    hour = hour or "00"
    minute = minute or "00"
    second = second or "00"
    try:
        dt = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
        )
    except ValueError:
        return None

    if tz and tz.upper() != "Z":
        tz_clean = tz.replace("'", "")
        sign = 1 if tz_clean.startswith("+") else -1
        tzh = int(tz_clean[1:3])
        tzm = int(tz_clean[3:5])
        offset = timezone(sign * (datetime.min.replace(hour=tzh, minute=tzm) - datetime.min))
        dt = dt.replace(tzinfo=offset)
        return dt.astimezone(timezone.utc).isoformat()

    if tz and tz.upper() == "Z":
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    value = value.replace("\x00", "")
    value = re.sub(r"[\x01-\x08\x0B\x0C\x0E-\x1F]", "", value)
    return re.sub(r"\s+", " ", value).strip()


def rect_to_list(rect: fitz.Rect) -> list[float]:
    return [round(float(rect.x0), 3), round(float(rect.y0), 3), round(float(rect.x1), 3), round(float(rect.y1), 3)]


def color_to_list(stroke: Any) -> list[float]:
    if isinstance(stroke, (list, tuple)):
        return [round(float(x), 4) for x in stroke]
    return []


def build_id(file_path: Path, page: int, subtype: str, comment_text: str, bbox: list[float]) -> str:
    payload = f"{file_path.resolve()}|{page}|{subtype}|{comment_text}|{bbox}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _xy(point: Any) -> tuple[float, float] | None:
    if point is None:
        return None
    if hasattr(point, "x") and hasattr(point, "y"):
        return float(point.x), float(point.y)
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        return float(point[0]), float(point[1])
    return None


def quads_from_vertices(vertices: list[Any] | None) -> list[list[float]]:
    if not vertices:
        return []
    quads: list[list[float]] = []
    for idx in range(0, len(vertices), 4):
        chunk = vertices[idx : idx + 4]
        if len(chunk) != 4:
            continue
        flattened: list[float] = []
        for pt in chunk:
            xy = _xy(pt)
            if xy is None:
                flattened = []
                break
            flattened.extend([round(xy[0], 3), round(xy[1], 3)])
        if len(flattened) != 8:
            continue
        quads.append(flattened)
    return quads


def extract_text_from_quads(page: fitz.Page, vertices: list[Any] | None) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if not vertices:
        return "", ["missing_quadpoints"]
    texts: list[str] = []
    for idx in range(0, len(vertices), 4):
        chunk = vertices[idx : idx + 4]
        if len(chunk) != 4:
            warnings.append("invalid_quad_chunk")
            continue
        norm_points = []
        for pt in chunk:
            xy = _xy(pt)
            if xy is None:
                warnings.append("invalid_quad_point")
                norm_points = []
                break
            norm_points.append(fitz.Point(xy[0], xy[1]))
        if len(norm_points) != 4:
            continue
        quad = fitz.Quad(norm_points)
        rect = quad.rect
        rect = fitz.Rect(rect.x0 - 1, rect.y0 - 1, rect.x1 + 1, rect.y1 + 1)
        text = clean_text(page.get_text("text", clip=rect))
        if text:
            texts.append(text)
    if not texts:
        warnings.append("quoted_text_empty")
    return " ".join(texts).strip(), warnings


def extract_context(page_text: str, quoted_text: str, limit: int) -> str:
    if not quoted_text:
        return ""
    lowered_page = page_text.lower()
    lowered_quote = quoted_text.lower()
    idx = lowered_page.find(lowered_quote)
    if idx < 0:
        return ""
    start = max(0, idx - limit // 2)
    end = min(len(page_text), idx + len(quoted_text) + limit // 2)
    return clean_text(page_text[start:end])


def extract_pdf_comments(pdf_path: Path, type_filter: set[str], context_chars: int) -> tuple[list[CommentRecord], list[dict[str, Any]]]:
    records: list[CommentRecord] = []
    failures: list[dict[str, Any]] = []

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:  # noqa: BLE001
        failures.append({"file": str(pdf_path), "error": "open_failed", "detail": str(exc)})
        return records, failures

    seen_ids: set[str] = set()
    for page_index in range(len(doc)):
        try:
            page = doc[page_index]
            page_text = clean_text(page.get_text("text"))
            annot = page.first_annot
            while annot:
                info = annot.info or {}
                raw_subtype = annot.type[1] if annot.type else "Unknown"
                subtype = normalize_subtype(raw_subtype)
                if type_filter and subtype not in type_filter:
                    annot = annot.next
                    continue

                comment_text = clean_text(info.get("content", ""))
                quoted_text, quote_warnings = extract_text_from_quads(page, annot.vertices)
                if not quoted_text:
                    quoted_text = clean_text(page.get_text("text", clip=annot.rect))
                context_text = extract_context(page_text, quoted_text, context_chars)

                warnings = list(quote_warnings)
                if page.rotation:
                    warnings.append("rotated_page")
                if not page_text:
                    warnings.append("text_layer_empty")

                bbox = rect_to_list(annot.rect)
                record_id = build_id(pdf_path, page_index + 1, subtype, comment_text or quoted_text, bbox)
                if record_id in seen_ids:
                    annot = annot.next
                    continue
                seen_ids.add(record_id)

                confidence = 0.4
                if quoted_text:
                    confidence += 0.35
                if comment_text:
                    confidence += 0.2
                if not warnings:
                    confidence += 0.05
                confidence = min(1.0, round(confidence, 3))

                record = CommentRecord(
                    id=record_id,
                    file=str(pdf_path),
                    page=page_index + 1,
                    subtype=subtype,
                    author=clean_text(info.get("title", "")),
                    comment_text=comment_text,
                    quoted_text=quoted_text,
                    context_text=context_text,
                    created_at=parse_pdf_date(info.get("creationDate")),
                    modified_at=parse_pdf_date(info.get("modDate")),
                    bbox=bbox,
                    quadpoints=quads_from_vertices(annot.vertices),
                    color=color_to_list(annot.colors.get("stroke") if annot.colors else None),
                    extraction_confidence=confidence,
                    warnings=warnings,
                    raw={
                        "subtype": raw_subtype,
                        "name": clean_text(info.get("name", "")),
                        "subject": clean_text(info.get("subject", "")),
                    },
                )
                records.append(record)
                annot = annot.next
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "file": str(pdf_path),
                    "page": page_index + 1,
                    "error": "page_processing_failed",
                    "detail": str(exc),
                }
            )
    doc.close()
    return records, failures


def discover_pdfs(path: Path, recursive: bool) -> list[Path]:
    if path.is_file() and path.suffix.lower() == ".pdf":
        return [path]
    if path.is_dir():
        pattern = "**/*.pdf" if recursive else "*.pdf"
        return sorted(path.glob(pattern))
    return []


def write_jsonl(path: Path, records: Iterable[CommentRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")


def write_csv(path: Path, records: list[CommentRecord]) -> None:
    if not records:
        with path.open("w", encoding="utf-8", newline="") as handle:
            handle.write("")
        return
    rows = [asdict(record) for record in records]
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            row["bbox"] = json.dumps(row["bbox"], ensure_ascii=False)
            row["quadpoints"] = json.dumps(row["quadpoints"], ensure_ascii=False)
            row["color"] = json.dumps(row["color"], ensure_ascii=False)
            row["warnings"] = json.dumps(row["warnings"], ensure_ascii=False)
            row["raw"] = json.dumps(row["raw"], ensure_ascii=False)
            writer.writerow(row)


def write_txt(path: Path, records: list[CommentRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for record in records:
            handle.write(f"Page {record.page}\n")
            handle.write(f"Comment: {record.comment_text or '-'}\n")
            handle.write(f"Quoted: {record.quoted_text or ''}\n")
            handle.write("\n")


def write_failures(path: Path, failures: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        for item in failures:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser()
    type_filter = {x.strip().lower() for x in args.types.split(",") if x.strip()}

    pdfs = discover_pdfs(input_path, args.recursive)
    if not pdfs:
        print(f"No PDF files found in: {input_path}", file=sys.stderr)
        return 2

    all_records: list[CommentRecord] = []
    all_failures: list[dict[str, Any]] = []
    succeeded = 0

    for pdf_path in pdfs:
        records, failures = extract_pdf_comments(pdf_path, type_filter, args.context_chars)
        all_records.extend(records)
        all_failures.extend(failures)
        open_failed = any(f.get("error") == "open_failed" and f.get("file") == str(pdf_path) for f in failures)
        if not open_failed:
            succeeded += 1
        if args.verbose:
            print(f"Processed: {pdf_path} | records={len(records)} failures={len(failures)}")
        if failures and not args.skip_errors:
            print(f"Failed processing {pdf_path}. Use --skip-errors to continue.", file=sys.stderr)
            failure_path = Path(args.failure_log) if args.failure_log else output_path.with_suffix(output_path.suffix + ".failures.jsonl")
            write_failures(failure_path, all_failures)
            return 1

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if args.format == "jsonl":
        write_jsonl(output_path, all_records)
    elif args.format == "csv":
        write_csv(output_path, all_records)
    else:
        write_txt(output_path, all_records)

    failure_path = Path(args.failure_log) if args.failure_log else output_path.with_suffix(output_path.suffix + ".failures.jsonl")
    write_failures(failure_path, all_failures)

    print(
        "Summary: "
        f"files_total={len(pdfs)} files_succeeded={succeeded} "
        f"records={len(all_records)} failures={len(all_failures)} output={output_path}"
    )
    if all_failures:
        print(f"Failure log: {failure_path}")
    return 0 if not all_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
