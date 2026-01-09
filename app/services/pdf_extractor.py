# app/repos/pdf_extractor.py
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
import tempfile
import os
from typing import List, Tuple

OCR_ENABLE = os.getenv("OCR_ENABLE", "true").lower() == "true"
OCR_MIN_TEXT_CHARS = int(os.getenv("OCR_MIN_TEXT_CHARS", 500))
OCR_DPI = int(os.getenv("OCR_DPI", 220))
OCR_LANG = os.getenv("OCR_LANG", "eng")


def extract_pages(pdf_bytes: bytes) -> Tuple[List[str], int, int, List[int]]:
    """
    Extract text from PDF pages.
    OCR fallback if text is missing or too small.

    Returns:
    - page_texts
    - page_count
    - total_words
    - ocr_pages
    """

    texts: List[str] = []
    ocr_pages: List[int] = []

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf_bytes)
        pdf_path = f.name

    try:
        reader = PdfReader(pdf_path)
        page_count = len(reader.pages)

        for i, page in enumerate(reader.pages):
            page_num = i + 1

            # -------- normal extraction --------
            try:
                raw_text = (page.extract_text() or "").strip()
            except Exception:
                raw_text = ""

            final_text = raw_text

            # -------- OCR decision --------
            use_ocr = (
                OCR_ENABLE
                and len(raw_text) < OCR_MIN_TEXT_CHARS
            )

            if use_ocr:
                try:
                    images = convert_from_path(
                        pdf_path,
                        dpi=OCR_DPI,
                        first_page=page_num,
                        last_page=page_num,
                    )

                    ocr_text = pytesseract.image_to_string(
                        images[0],
                        lang=OCR_LANG
                    ).strip()

                    # prefer OCR if it gives more text
                    if len(ocr_text) > len(raw_text):
                        final_text = ocr_text
                        ocr_pages.append(page_num)

                except Exception:
                    pass

            # IMPORTANT: only append non-empty text
            if final_text.strip():
                texts.append(final_text)

        full_text = "\n\n".join(texts)
        total_words = len(full_text.split())

        return texts, page_count, total_words, ocr_pages

    finally:
        try:
            os.remove(pdf_path)
        except Exception:
            pass
