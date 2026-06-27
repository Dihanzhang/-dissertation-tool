import fitz
doc = fitz.open(r'C:\Users\dihan\OneDrive\USC\Textbooks\APA 2020 7th Ed.pdf')
print(f"Total pages: {len(doc)}")

# Search for Chapter 9 and 10 headings by scanning pages
for page_num in range(len(doc)):
    page = doc[page_num]
    text = page.get_text()
    if any(kw in text for kw in ['CHAPTER 9', 'Chapter 9', 'chapter 9', 'CHAPTER 10', 'Chapter 10']):
        lines = text.split('\n')
        for line in lines[:10]:
            if line.strip():
                print(f"Page {page_num+1}: {line.strip()[:80]}")
        break

# Also scan for section numbers like 9.19, 10.1 etc
hits = []
for page_num in range(180, 350):
    page = doc[page_num]
    text = page.get_text()
    lines = text.split('\n')
    for line in lines[:5]:
        stripped = line.strip()
        if stripped and (stripped.startswith('9.') or stripped.startswith('10.') or
                        'Reference' in stripped or 'REFERENCE' in stripped):
            hits.append((page_num+1, stripped[:100]))

for page_num, text in hits[:50]:
    print(f"Page {page_num}: {text}")
