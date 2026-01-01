import pdfplumber
import json

def inspect_resume(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        first_page = pdf.pages[0]
        
        # Extract characters to see fonts/sizes
        chars = first_page.chars
        fonts = {}
        for char in chars:
            font_name = char['fontname']
            size = round(char['size'], 2)
            color = char.get('non_stroking_color', 'None')
            
            key = f"{font_name} | {size} | {color}"
            fonts[key] = fonts.get(key, 0) + 1
            
        sorted_fonts = sorted(fonts.items(), key=lambda x: x[1], reverse=True)
        
        # Extract words with their positions to understand layout
        words = first_page.extract_words()
        
        print(json.dumps({
            "page_width": float(first_page.width),
            "page_height": float(first_page.height),
            "top_fonts": sorted_fonts[:10],
            "sample_words": words[:20]
        }, indent=2))

if __name__ == "__main__":
    import sys
    inspect_resume(sys.argv[1])
