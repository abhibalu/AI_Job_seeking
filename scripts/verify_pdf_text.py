
import fitz  # PyMuPDF

def check_pdf_text(filepath):
    try:
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        
        print(f"--- Extracted Text from {filepath} ---")
        print(text)
        print("----------------------------------------")
        
        # Check for specific split
        name_part_1 = "ABHIJITH SIVADAS M"
        name_part_2 = "OOTHEDATH"
        
        if f"{name_part_1}\n{name_part_2}" in text:
            print("ALERT: Name is split with a newline character!")
        elif f"{name_part_1} {name_part_2}" in text:
            print("SUCCESS: Name is on a single line.")
        else:
            print("Name format not found exactly as expected. Checking for general splits...")
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if "ABHIJITH" in line:
                    print(f"Line {i}: {line}")
                    if i + 1 < len(lines):
                        print(f"Line {i+1}: {lines[i+1]}")
                        
    except Exception as e:
        print(f"Error reading PDF: {e}")

if __name__ == "__main__":
    check_pdf_text("/Users/abhijithm/Documents/Code/TailorAI/test/abhijith_test.pdf")
