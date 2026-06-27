import fitz
doc = fitz.open(r'C:\Users\dihan\OneDrive\USC\Textbooks\APA 2020 7th Ed.pdf')

# Chapter 11 on legal references - find it
output = []
for page_num in range(370, 420):
    page = doc[page_num]
    text = page.get_text()
    if any(kw in text for kw in ['LEGAL', 'Legal', 'statute', 'Statute', 'court', 'Court', 'regulation', '11.']):
        output.append(f"\n{'='*60}\nPDF PAGE {page_num+1}\n{'='*60}\n")
        output.append(text)

with open(r'C:\Users\dihan\dissertation-tool\backend\apa_ch11.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print(f"Extracted legal chapter pages, total chars: {sum(len(o) for o in output)}")
