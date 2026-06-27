import fitz
doc = fitz.open(r'C:\Users\dihan\OneDrive\USC\Textbooks\APA 2020 7th Ed.pdf')

# Extract pages 295-430 (Chapters 9 and 10 based on page scan)
# Save to text file
output = []
for page_num in range(294, 430):  # 0-indexed, so page 295 = index 294
    page = doc[page_num]
    text = page.get_text()
    output.append(f"\n{'='*60}\nPDF PAGE {page_num+1}\n{'='*60}\n")
    output.append(text)

with open(r'C:\Users\dihan\dissertation-tool\backend\apa_ch9_10.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(output))

print(f"Extracted pages 295-430, total chars: {sum(len(o) for o in output)}")
