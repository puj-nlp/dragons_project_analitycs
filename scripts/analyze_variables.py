from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

VENDOR_DIR = Path(__file__).resolve().parents[1] / ".vendor" / "python"
if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))
VENDOR_DIR_ALT = Path(__file__).resolve().parents[1] / "vendor_python"
if VENDOR_DIR_ALT.exists():
    sys.path.insert(0, str(VENDOR_DIR_ALT))

import fitz
import pandas as pd
import yaml

from run_pilot_processing import HFModelClient, clean_text, deterministic_variables, utcnow


def extract_pdf_text(path: Path, max_pages: int | None = None, ocr: bool = True) -> dict[str, Any]:
    doc = fitz.open(str(path))
    pages = min(doc.page_count, max_pages or doc.page_count)
    embedded_parts = [doc[index].get_text() for index in range(pages)]
    embedded_text = clean_text("\n".join(embedded_parts))
    if len(embedded_text) >= 100 or not ocr:
        return {
            "method": "embedded_text",
            "page_count": doc.page_count,
            "pages_processed": pages,
            "text": embedded_text,
        }

    try:
        import easyocr
    except Exception as exc:
        return {
            "method": "ocr_unavailable",
            "page_count": doc.page_count,
            "pages_processed": pages,
            "text": embedded_text,
            "error": f"{type(exc).__name__}: {str(exc)[:500]}",
        }

    reader = easyocr.Reader(["es", "en"], gpu=False)
    ocr_parts: list[str] = []
    for index in range(pages):
        page = doc[index]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image_bytes = pix.tobytes("png")
        result = reader.readtext(image_bytes, detail=0, paragraph=True)
        ocr_parts.append("\n".join(result))
    return {
        "method": "easyocr",
        "page_count": doc.page_count,
        "pages_processed": pages,
        "text": clean_text("\n".join(ocr_parts)),
    }


def build_row(path: Path, text: str) -> pd.Series:
    return pd.Series({
        "document_id": path.stem,
        "mongo_id": None,
        "collection_name": "pabla_email_pdf",
        "source": "pabla_email",
        "strategy": "manual_pdf_test",
        "source_type": "email",
        "country_key": None,
        "language": "es",
        "created_at": None,
        "url": str(path),
        "title": path.stem,
        "text": text,
        "metadata": {},
        "raw_metadata": {},
        "char_count": len(text),
        "word_count": len(text.split()),
        "sentence_count": None,
        "paragraph_count": None,
        "lexical_density_proxy": None,
        "top_terms": None,
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Pabla email PDF with OCR and GLiNER.")
    parser.add_argument(
        "--pdf",
        default="temp/resource_index_page/Cooreo_1_pabla.pdf",
        help="Path to the Pabla email PDF.",
    )
    parser.add_argument("--config", default="config/pipeline_config.yml")
    parser.add_argument("--output-dir", default="data/processed/pabla_email_tests")
    parser.add_argument("--max-pages", type=int)
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--hf-model")
    args = parser.parse_args()

    started = time.time()
    pdf_path = Path(args.pdf)
    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    if args.hf_model:
        config.setdefault("hf_models", {}).setdefault("gliner", {})["model"] = args.hf_model
    extracted = extract_pdf_text(pdf_path, max_pages=args.max_pages, ocr=not args.no_ocr)
    row = build_row(pdf_path, extracted.get("text", ""))
    deterministic = deterministic_variables(row)
    hf_data, hf_meta = HFModelClient(config).annotate(row)

    output_dir = Path(args.output_dir) / f"{pdf_path.stem}_{utcnow().replace(':', '').replace('+', 'Z')}"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "extracted_text.txt").write_text(extracted.get("text", ""), encoding="utf-8")
    record = {
        "pdf": str(pdf_path),
        "computed_at": utcnow(),
        "elapsed_seconds": round(time.time() - started, 3),
        "extraction": {key: value for key, value in extracted.items() if key != "text"},
        "text_char_count": len(extracted.get("text", "")),
        "text_preview": extracted.get("text", "")[:1000],
        "deterministic_variables": deterministic,
        "hf_variables": hf_data,
        "hf_metadata": hf_meta,
    }
    (output_dir / "pabla_email_analysis.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps({"output_dir": str(output_dir), **record}, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
