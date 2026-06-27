import fitz
import sys

doc = fitz.open(r'C:\Users\dihan\OneDrive\USC\Textbooks\APA 2020 7th Ed.pdf')

def get_page_preview(start, end):
    for i in range(start, end):
        page = doc[i]
        text = page.get_text()
        if text.strip():
            first_line = text.strip().split('\n')[0][:120]
            print(f'PDF PAGE {i+1}: {first_line}')

def get_pages_text(start, end):
    result = []
    for i in range(start, end):
        page = doc[i]
        text = page.get_text()
        result.append(f'\n=== PDF PAGE {i+1} ===\n{text}')
    return '\n'.join(result)

mode = sys.argv[1] if len(sys.argv) > 1 else 'preview'
start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
end = int(sys.argv[3]) if len(sys.argv) > 3 else 20

if mode == 'preview':
    get_page_preview(start, end)
elif mode == 'text':
    print(get_pages_text(start, end))
elif mode == 'save':
    outfile = sys.argv[4] if len(sys.argv) > 4 else 'output.txt'
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(get_pages_text(start, end))
    print(f'Saved to {outfile}')
