from io import BytesIO
from pypdf import PdfReader


def extract_pdf_text(pdf_file):
    """
    PDF se text extract karta hai.
    UploadedFile, bytes aur file-like object support karta hai.
    """

    if isinstance(pdf_file, bytes):
        pdf_bytes = pdf_file

    elif hasattr(pdf_file, "getvalue"):
        pdf_bytes = pdf_file.getvalue()

    elif hasattr(pdf_file, "read"):
        pdf_file.seek(0)
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)

    else:
        raise TypeError("Invalid PDF file format.")

    if not pdf_bytes:
        raise ValueError("Uploaded PDF is empty.")

    reader = PdfReader(BytesIO(pdf_bytes))

    if reader.is_encrypted:
        raise ValueError("Password-protected PDFs are not supported.")

    extracted_text = []

    for page_number, page in enumerate(reader.pages, start=1):

        page_text = page.extract_text()

        if page_text:
            extracted_text.append(page_text)

    full_text = "\n\n".join(extracted_text).strip()

    if not full_text:
        raise ValueError(
            "No readable text found. This may be a scanned PDF."
        )

    return full_text


def split_text(text, chunk_size=1000, overlap=200):
    """
    Large PDF text ko smaller chunks mein divide karta hai.
    """

    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "Overlap must be non-negative and smaller than chunk size."
        )

    chunks = []

    start = 0

    while start < len(text):

        end = min(start + chunk_size, len(text))

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks