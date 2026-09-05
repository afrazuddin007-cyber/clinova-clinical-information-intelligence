import fitz  # PyMuPDF
import os
from pathlib import Path
from typing import Dict, Any, List


def parse_document(file_path: str) -> Dict[str, Any]:
    """
    Parses a PDF or image file.
    Extracts text per page, page count, page dimensions, and structured table content.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()

    if ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        return _parse_image(file_path)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")


def _reconstruct_table_rows_from_words(page: fitz.Page) -> str:
    """
    Reconstructs table-like rows from word-level bounding boxes.
    Groups words on the same approximate y-coordinate into rows,
    then joins columns left-to-right separated by ' | '.

    This preserves lab table structure (TestName | Value | Unit | RefRange)
    that would otherwise be lost in plain text extraction.
    """
    words = page.get_text("words")  # list of (x0,y0,x1,y1,text,block,line,word)
    if not words:
        return ""

    # Group words into rows by their vertical midpoint (y0+y1)/2
    # Cluster tolerance: words within ~4 pts vertically are on the same row
    Y_TOLERANCE = 4.0
    rows: List[List[tuple]] = []
    for word_tuple in sorted(words, key=lambda w: (w[1], w[0])):  # sort by y, then x
        x0, y0, x1, y1, text = word_tuple[0], word_tuple[1], word_tuple[2], word_tuple[3], word_tuple[4]
        mid_y = (y0 + y1) / 2.0
        placed = False
        for row in rows:
            row_mid_y = sum((r[1] + r[3]) / 2.0 for r in row) / len(row)
            if abs(mid_y - row_mid_y) <= Y_TOLERANCE:
                row.append((x0, y0, x1, y1, text))
                placed = True
                break
        if not placed:
            rows.append([(x0, y0, x1, y1, text)])

    # Within each row, sort words left-to-right by x0
    result_lines = []
    for row in rows:
        row_sorted = sorted(row, key=lambda w: w[0])
        # Build columns: detect large horizontal gaps as column separators
        cols: List[str] = []
        current_col_words: List[str] = []
        prev_x1 = None
        for w in row_sorted:
            x0, _, _, _, text = w[0], w[1], w[2], w[3], w[4]
            if prev_x1 is not None and (x0 - prev_x1) >= 12.0:
                # Gap detected — flush current column
                if current_col_words:
                    cols.append(" ".join(current_col_words))
                current_col_words = [text]
            else:
                current_col_words.append(text)
            prev_x1 = w[2]
        if current_col_words:
            cols.append(" ".join(current_col_words))

        if cols:
            result_lines.append(" | ".join(cols))

    return "\n".join(result_lines)


def _try_native_table_extraction(page: fitz.Page) -> str:
    """
    Attempts PyMuPDF 1.23+ native table finder.
    Falls back to empty string if unavailable or no tables found.
    """
    try:
        tables = page.find_tables()
        if not tables or not tables.tables:
            return ""
        lines = []
        for table in tables.tables:
            for row in table.extract():
                # row is a list of cell strings (may be None)
                cells = [str(c).strip() if c is not None else "" for c in row]
                # Skip rows that are entirely blank
                if any(c for c in cells):
                    lines.append(" | ".join(cells))
        return "\n".join(lines)
    except AttributeError:
        # find_tables() not available in this PyMuPDF version
        return ""
    except Exception:
        return ""


def _parse_pdf(pdf_path: str) -> Dict[str, Any]:
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    pages_data: List[Dict[str, Any]] = []
    full_text_parts: List[str] = []
    full_structured_parts: List[str] = []

    for page_num in range(page_count):
        page = doc.load_page(page_num)
        plain_text = page.get_text("text")

        # Try native table detection first (PyMuPDF 1.23+)
        native_tables = _try_native_table_extraction(page)

        # Always reconstruct from word positions as a reliable fallback
        word_reconstructed = _reconstruct_table_rows_from_words(page)

        # Choose the best structured representation:
        # native tables if found, otherwise word-reconstructed
        structured_text = native_tables if native_tables.strip() else word_reconstructed

        page_header = f"=== PAGE {page_num + 1} ==="

        pages_data.append({
            "page_number": page_num + 1,
            "text": plain_text,
            "table_text": structured_text,
            "rect": [page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1]
        })

        full_text_parts.append(f"{page_header}\n{plain_text}")
        if structured_text.strip():
            full_structured_parts.append(f"{page_header}\n{structured_text}")

    doc.close()

    # Build a combined document that prioritises table structure.
    # The structured section leads so Gemini sees column boundaries clearly.
    combined_parts = []
    if full_structured_parts:
        combined_parts.append(
            "--- STRUCTURED TABLE CONTENT (column-aligned rows) ---\n" +
            "\n".join(full_structured_parts)
        )
    combined_parts.append(
        "--- PLAIN TEXT CONTENT ---\n" +
        "\n".join(full_text_parts)
    )

    return {
        "file_type": "application/pdf",
        "page_count": page_count,
        "pages": pages_data,
        "full_text": "\n\n".join(combined_parts)
    }


def _parse_image(image_path: str) -> Dict[str, Any]:
    # Single-page image; text extraction handled by Gemini vision
    return {
        "file_type": "image",
        "page_count": 1,
        "pages": [{
            "page_number": 1,
            "text": "",
            "table_text": "",
            "path": image_path
        }],
        "full_text": ""
    }
