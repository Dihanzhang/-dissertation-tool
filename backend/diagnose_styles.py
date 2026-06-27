"""Diagnose paragraph styles in a .docx file."""
import sys
from docx import Document

path = sys.argv[1] if len(sys.argv) > 1 else input("Path to .docx: ").strip()
doc = Document(path)

print(f"\n{'IDX':>4}  {'STYLE':<30}  TEXT[:80]")
print("-" * 120)
for i, para in enumerate(doc.paragraphs):
    text = para.text.strip()
    if not text:
        continue
    style = para.style.name if para.style else "(none)"
    print(f"{i:>4}  {style:<30}  {text[:80]}")
