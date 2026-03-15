"""
PDF/TXT/Excel text extraction utility
"""
import io
import traceback


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from a file based on extension."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith((".xlsx", ".xls")):
        return extract_text_from_excel(file_bytes)
    elif filename_lower.endswith((".txt", ".md", ".csv")):
        return extract_text_from_txt(file_bytes)
    else:
        # Default to text
        return extract_text_from_txt(file_bytes)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text_parts = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as e:
        traceback.print_exc()
        return f"Error extracting PDF text: {str(e)}"


def extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode raw bytes to string."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1")
        except Exception:
            return file_bytes.decode("utf-8", errors="replace")


def extract_text_from_excel(file_bytes: bytes) -> str:
    """Extract text representation from Excel."""
    try:
        import pandas as pd
        df = pd.read_excel(io.BytesIO(file_bytes))
        # Convert DataFrame to readable text
        text_parts = [f"Columns: {', '.join(df.columns.tolist())}"]
        text_parts.append(f"Rows: {len(df)}")
        text_parts.append("")
        # Include first 50 rows as text
        for idx, row in df.head(50).iterrows():
            row_text = " | ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
            text_parts.append(row_text)
        return "\n".join(text_parts)
    except Exception as e:
        traceback.print_exc()
        return f"Error extracting Excel text: {str(e)}"
