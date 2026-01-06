import pdfplumber
import os

pdf_path = "/Users/abhijithm/Documents/Code/TailorAI/test/abhijith_sivadas_resume_retail.pdf"
output_path = "/Users/abhijithm/Documents/Code/TailorAI/test/abhijith_sivadas_resume_retail.txt"

def extract_text(pdf_path, output_path):
    print(f"Extracting text from: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
        return

    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    full_text += text + "\n\n"
                    print(f"Extracted page {i+1}")
        
        with open(output_path, "w") as f:
            f.write(full_text)
            
        print(f"Successfully saved content to: {output_path}")
        print("-" * 30)
        print(full_text[:500] + "...") # Preview
        
    except Exception as e:
        print(f"Error extracting PDF: {e}")

if __name__ == "__main__":
    extract_text(pdf_path, output_path)
