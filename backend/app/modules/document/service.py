from fastapi import HTTPException, UploadFile
from prisma.fields import Json
from starlette.concurrency import run_in_threadpool
from pypdf import PdfReader

from .model import Document
from app.db import db

try:
    import fitz
except ImportError:  # pragma: no cover - fallback is exercised when PyMuPDF is unavailable
    fitz = None


MAX_CHUNK_TOKENS = 500
OVERLAP_TOKENS = 75
HEADING_FONT_SIZE = 14.0
SHORT_BLOCK_CHARS = 60
MIN_COLUMN_GAP = 72.0
MIN_GAP_HEIGHT = 28.0


def _normalize_whitespace(text: str) -> str:
    return " ".join(text.replace("\x00", " ").split()).strip()


def _approx_token_count(text: str) -> int:
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def _classify_block(text: str, avg_font_size: float, is_bold: bool) -> str:
    stripped = text.lstrip()
    if not stripped:
        return "paragraph"

    if stripped.startswith(("-", "*", "\u2022", "\u25aa", "\u25cf")):
        return "list"

    looks_like_sentence = stripped.endswith((".", "!", "?", ";", ":"))
    few_lines = text.count("\n") <= 1
    if (
        len(text) <= 80
        and few_lines
        and not looks_like_sentence
        and (avg_font_size >= HEADING_FONT_SIZE or (is_bold and len(text) <= SHORT_BLOCK_CHARS))
    ):
        return "heading"

    return "paragraph"


def _get_bbox_axis(block: dict, index: int, default: float) -> float:
    bbox = block.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        try:
            return float(bbox[index])
        except (TypeError, ValueError):
            return default
    return default


def _detect_column_split(page_blocks: list[dict]) -> float | None:
    x_positions = sorted(
        {
            _get_bbox_axis(block, 0, 0.0)
            for block in page_blocks
            if isinstance(block.get("bbox"), list) and len(block["bbox"]) == 4
        }
    )
    if len(x_positions) < 2:
        return None

    best_gap = 0.0
    split = None
    for left, right in zip(x_positions, x_positions[1:]):
        gap = right - left
        if gap < MIN_COLUMN_GAP or gap <= best_gap:
            continue
        split = left + gap / 2
        best_gap = gap

    if split is None:
        return None

    left_count = sum(1 for block in page_blocks if _get_bbox_axis(block, 0, 0.0) < split)
    right_count = sum(1 for block in page_blocks if _get_bbox_axis(block, 0, 0.0) >= split)
    if left_count < 2 or right_count < 2:
        return None

    return split


def _order_blocks_for_chunking(blocks: list[dict]) -> list[dict]:
    ordered_blocks: list[dict] = []

    for page_number in sorted({block["page"] for block in blocks}):
        page_blocks = [block.copy() for block in blocks if block["page"] == page_number]
        split = _detect_column_split(page_blocks)

        # Sorting by inferred column first keeps sidebars and body text from being interleaved.
        for block in page_blocks:
            bbox = block.get("bbox")
            if split is not None and isinstance(bbox, list) and len(bbox) == 4:
                block["_column"] = 0 if _get_bbox_axis(block, 0, 0.0) < split else 1
            else:
                block["_column"] = 0

        page_blocks.sort(
            key=lambda block: (
                block["_column"],
                _get_bbox_axis(block, 1, float(block["blockIndex"])),
                _get_bbox_axis(block, 0, 0.0),
                block["blockIndex"],
            )
        )
        ordered_blocks.extend(page_blocks)

    return ordered_blocks


def _is_short_context_block(block: dict) -> bool:
    text = (block.get("text") or "").strip()
    if not text:
        return False
    if block.get("type") == "heading":
        return True
    return len(text) <= SHORT_BLOCK_CHARS


def _should_flush_before_block(current_blocks: list[dict], next_block: dict) -> bool:
    if not current_blocks:
        return False

    previous_block = current_blocks[-1]
    if previous_block["page"] != next_block["page"]:
        return True

    if previous_block.get("_column", 0) != next_block.get("_column", 0):
        return True

    prev_type = previous_block.get("type")
    next_type = next_block.get("type")
    if next_type == "heading" and prev_type != "heading":
        return True

    prev_y1 = _get_bbox_axis(previous_block, 3, 0.0)
    next_y0 = _get_bbox_axis(next_block, 1, 0.0)
    if prev_y1 and next_y0 and next_y0 - prev_y1 >= MIN_GAP_HEIGHT:
        if not (_is_short_context_block(previous_block) or _is_short_context_block(next_block)):
            return True

    return False


def _extract_pdf_blocks_with_pymupdf(file_bytes: bytes) -> list[dict]:
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    blocks: list[dict] = []
    try:
        for page_index, page in enumerate(doc, start=1):
            page_dict = page.get_text("dict", sort=True)
            for block_index, block in enumerate(page_dict.get("blocks", [])):
                if block.get("type") != 0:
                    continue

                lines = block.get("lines", [])
                fragments: list[str] = []
                font_sizes: list[float] = []
                bold_flags: list[bool] = []

                for line in lines:
                    line_fragments: list[str] = []
                    for span in line.get("spans", []):
                        span_text = _normalize_whitespace(span.get("text", ""))
                        if not span_text:
                            continue

                        line_fragments.append(span_text)
                        font_sizes.append(float(span.get("size", 0.0) or 0.0))
                        font_name = str(span.get("font", "")).lower()
                        bold_flags.append("bold" in font_name or span.get("flags", 0) & 16 > 0)

                    line_text = " ".join(line_fragments).strip()
                    if line_text:
                        fragments.append(line_text)

                text = "\n".join(fragments).strip()
                if not text:
                    continue

                avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 0.0
                is_bold = any(bold_flags)
                blocks.append(
                    {
                        "page": page_index,
                        "blockIndex": block_index,
                        "type": _classify_block(text, avg_font_size, is_bold),
                        "text": text,
                        "bbox": [round(value, 2) for value in block.get("bbox", [])],
                        "avgFontSize": round(avg_font_size, 2),
                    }
                )
    finally:
        doc.close()

    return blocks


def _extract_pdf_blocks_with_pypdf(file_obj) -> list[dict]:
    file_obj.seek(0)
    reader = PdfReader(file_obj)
    blocks: list[dict] = []

    for page_index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        paragraphs = [
            _normalize_whitespace(part)
            for part in page_text.split("\n\n")
            if _normalize_whitespace(part)
        ]
        for block_index, paragraph in enumerate(paragraphs):
            blocks.append(
                {
                    "page": page_index,
                    "blockIndex": block_index,
                    "type": "paragraph",
                    "text": paragraph,
                    "bbox": None,
                    "avgFontSize": None,
                }
            )

    return blocks


def _extract_pdf_content(file_obj) -> dict:
    file_obj.seek(0)
    file_bytes = file_obj.read()

    try:
        blocks = _extract_pdf_blocks_with_pymupdf(file_bytes)
    except Exception:
        blocks = _extract_pdf_blocks_with_pypdf(file_obj)

    ordered_blocks = _order_blocks_for_chunking(blocks)
    content = "\n\n".join(block["text"] for block in ordered_blocks).strip()
    chunks = _build_chunks(ordered_blocks)

    return {
        "content": content,
        "extractedBlocks": blocks,
        "chunks": chunks,
    }


def _build_chunks(blocks: list[dict]) -> list[dict]:
    chunks: list[dict] = []
    current_blocks: list[dict] = []
    active_heading: str | None = None
    current_chunk_heading: str | None = None
    chunk_index = 0

    def flush_chunk(block_buffer: list[dict], section_title: str | None, index: int) -> dict | None:
        text_parts = [block["text"] for block in block_buffer if block.get("text")]
        text = "\n\n".join(text_parts).strip()
        if not text:
            return None

        return {
            "chunkIndex": index,
            "text": text,
            "pages": sorted({block["page"] for block in block_buffer}),
            "sectionTitle": section_title,
            "blockRefs": [
                {"page": block["page"], "blockIndex": block["blockIndex"]}
                for block in block_buffer
            ],
            "tokenCount": _approx_token_count(text),
        }

    for block in blocks:
        block_type = block.get("type")
        block_heading = active_heading
        if block_type == "heading":
            block_heading = block["text"]

        # Flush on layout or section boundaries before applying the size budget.
        if _should_flush_before_block(current_blocks, block):
            chunk = flush_chunk(current_blocks, current_chunk_heading, chunk_index)
            if chunk is not None:
                chunks.append(chunk)
                chunk_index += 1
            current_blocks = []
            current_chunk_heading = block_heading if block_type != "heading" else None

        candidate_blocks = current_blocks + [block]
        candidate_text = "\n\n".join(item["text"] for item in candidate_blocks)

        if current_blocks and _approx_token_count(candidate_text) > MAX_CHUNK_TOKENS:
            chunk = flush_chunk(current_blocks, current_chunk_heading, chunk_index)
            if chunk is not None:
                chunks.append(chunk)
                chunk_index += 1

            overlap_blocks: list[dict] = []
            overlap_tokens = 0
            for overlap_block in reversed(current_blocks):
                overlap_blocks.insert(0, overlap_block)
                overlap_tokens += _approx_token_count(overlap_block["text"])
                if overlap_tokens >= OVERLAP_TOKENS:
                    break

            current_blocks = overlap_blocks + [block]
            current_chunk_heading = block_heading
        else:
            current_blocks = candidate_blocks
            if current_chunk_heading is None:
                current_chunk_heading = block_heading

        if block_type == "heading":
            active_heading = block["text"]

    if current_blocks:
        chunk = flush_chunk(current_blocks, current_chunk_heading, chunk_index)
        if chunk is not None:
            chunks.append(chunk)

    return chunks


def _serialize_chunk_rows(chunks: list[dict]) -> list[dict]:
    # Chunk rows become the retrieval source of truth, so JSON metadata is normalized here.
    return [
        {
            "chunkIndex": chunk["chunkIndex"],
            "text": chunk["text"],
            "sectionTitle": chunk.get("sectionTitle"),
            "pages": Json(chunk["pages"]),
            "blockRefs": Json(chunk["blockRefs"]),
            "tokenCount": chunk["tokenCount"],
        }
        for chunk in chunks
    ]


async def extract_content(file: UploadFile) -> dict:
    await file.seek(0)
    return await run_in_threadpool(_extract_pdf_content, file.file)


async def upload_document(file: UploadFile, collection_id: int) -> Document:
    extracted = None
    if file.content_type == "application/pdf":
        extracted = await extract_content(file)
    else:
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    document_data = {
        "name": file.filename,
        "content": extracted["content"],
        "collectionId": collection_id,
    }

    if extracted["extractedBlocks"] is not None:
        document_data["extractedBlocks"] = Json(extracted["extractedBlocks"])

    document = await db.document.create(data=document_data)

    chunk_rows = _serialize_chunk_rows(extracted["chunks"])
    if chunk_rows:
        await db.documentchunk.create_many(
            data=[{"documentId": document.id, **chunk_row} for chunk_row in chunk_rows]
        )

    document = await db.document.find_unique(
        where={"id": document.id},
        include={"chunks": True},
    )
    return Document.model_validate(document)
