import typst
try:
    typst.compile("test.typ", output="test.pdf")
    print("Typst compile success")
except Exception as e:
    print(f"Typst compile failed: {e}")
