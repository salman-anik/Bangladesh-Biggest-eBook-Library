"""
OCR Processor for Bangladesh eBook Library.
Supports text extraction and OCR checking for scanned PDFs.
"""

from typing import Dict, Any

def check_pdf_scanned(file_path: str) -> Dict[str, Any]:
    """
    Checks if a PDF has selectable text or is a scanned image.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        total_pages = len(doc)
        text_found = False
        for i in range(min(total_pages, 5)):
            page_text = doc[i].get_text()
            if page_text and len(page_text.strip()) > 50:
                text_found = True
                break
        doc.close()
        return {
            "total_pages": total_pages,
            "has_selectable_text": text_found,
            "requires_ocr": not text_found
        }
    except Exception as e:
        return {
            "error": str(e),
            "has_selectable_text": False,
            "requires_ocr": True
        }
