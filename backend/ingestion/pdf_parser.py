import pdfplumber

def extract_pages(pdf_path: str):
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ''
            text = text.strip()
            if text:
                pages.append((i, text))
    return pages