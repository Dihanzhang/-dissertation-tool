"""
Script to extract APA Chapter 5 text from PDF using PyMuPDF (fitz).
Run: python extract_apa_ch5.py
Output: apa_ch5_raw.txt in same directory
"""
import fitz
import sys

PDF_PATH = r'C:\Users\dihan\OneDrive\USC\Textbooks\APA 2020 7th Ed.pdf'
OUTPUT_PATH = r'C:\Users\dihan\dissertation-tool\backend\apa_ch5_raw.txt'

doc = fitz.open(PDF_PATH)
print(f'Total PDF pages: {len(doc)}')

# Step 1: Find chapter boundaries by scanning pages 120-210
ch5_start = None
ch6_start = None

for pg in range(115, 215):
    page = doc[pg]
    text = page.get_text()
    text_upper = text.upper()

    # Look for Chapter 5 start
    if ch5_start is None:
        if ('CHAPTER 5' in text_upper or
            'BIAS-FREE LANGUAGE' in text_upper or
            ('5.1' in text and 'bias' in text.lower())):
            ch5_start = pg
            print(f'Chapter 5 candidate at PDF page {pg+1}')
            print(repr(text[:300]))

    # Look for Chapter 6 start (only after we found Ch5)
    elif ch6_start is None:
        if ('CHAPTER 6' in text_upper or
            ('6.1' in text and pg > ch5_start + 10)):
            ch6_start = pg
            print(f'Chapter 6 candidate at PDF page {pg+1}')
            print(repr(text[:300]))
            break

print(f'\nch5_start={ch5_start}, ch6_start={ch6_start}')

if ch5_start is None:
    print('ERROR: Could not find Chapter 5 start. Trying broader scan...')
    for pg in range(100, 220):
        text = doc[pg].get_text()
        if 'bias' in text.lower()[:200]:
            print(f'Page {pg+1}: {text[:200]}')
    sys.exit(1)

if ch6_start is None:
    print('WARNING: Could not find Chapter 6 start. Extracting 50 pages from Ch5 start.')
    ch6_start = ch5_start + 50

# Step 2: Extract Chapter 5 text
full_text = ''
for pg in range(ch5_start, ch6_start):
    page_text = doc[pg].get_text()
    full_text += f'\n\n=== PDF PAGE {pg+1} ===\n\n'
    full_text += page_text

with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(full_text)

print(f'\nSaved {len(full_text)} characters ({ch6_start - ch5_start} pages) to:')
print(OUTPUT_PATH)
doc.close()
