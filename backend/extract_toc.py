import fitz
doc = fitz.open(r'C:\Users\dihan\OneDrive\USC\Textbooks\APA 2020 7th Ed.pdf')
toc = doc.get_toc()
print(f"TOC entries: {len(toc)}")
for i, item in enumerate(toc):
    level, title, page = item
    print(f"  {i}: Level {level}, Page {page}: {title}")
