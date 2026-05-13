"""Markdown → HTML → PDF with Rappi branding."""
import io
import markdown as md
from xhtml2pdf import pisa

CSS = """
body { font-family: Helvetica, Arial, sans-serif; color: #1A1A1A; font-size: 11pt; line-height: 1.5; }
h1 { color: #FF441F; border-bottom: 3px solid #FF441F; padding-bottom: 6px; }
h2 { color: #FF441F; margin-top: 24px; }
h3 { color: #333; margin-top: 16px; }
strong { color: #1A1A1A; }
ul { padding-left: 20px; }
li { margin-bottom: 4px; }
hr { border: none; border-top: 1px solid #ccc; margin: 24px 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 6px 10px; text-align: left; }
th { background: #FFE9E0; }
"""


def markdown_to_pdf_bytes(markdown_text: str) -> bytes:
    html_body = md.markdown(markdown_text, extensions=["tables", "fenced_code"])
    full_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{CSS}</style></head><body>{html_body}</body></html>"""
    buf = io.BytesIO()
    pisa.CreatePDF(full_html, dest=buf)
    return buf.getvalue()
