import fitz
doc = fitz.open(r'C:\Users\dihan\OneDrive\USC\Textbooks\APA 2020 7th Ed.pdf')

# Chapter 6 covers sections 6.14, 6.17, 6.22 - need to find page range
# Chapter 6 is on mechanics of style - probably pages 155-200 range
# Let's search for section 6.14 and 6.17
output = []
for page_num in range(140, 230):
    page = doc[page_num]
    text = page.get_text()
    if any(kw in text for kw in ['6.14', '6.17', '6.22', '6.23', 'title case', 'sentence case', 'italicize', 'Italic']):
        output.append(f"\n{'='*60}\nPDF PAGE {page_num+1}\n{'='*60}\n")
        output.append(text)

with open(r'C:\Users\dihan\dissertation-tool\backend\apa_ch6.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print(f"Extracted pages with title/italic rules, total chars: {sum(len(o) for o in output)}")
print(f"Number of pages extracted: {len([o for o in output if 'PDF PAGE' in o])}")
