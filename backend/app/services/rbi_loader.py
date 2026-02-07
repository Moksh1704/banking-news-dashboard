import fitz  # PyMuPDF

def load_rbi_pdf(file_path):

    docs = []

    pdf = fitz.open(file_path)

    for page_num in range(len(pdf)):

        page = pdf[page_num]
        text = page.get_text()

        if text.strip():

            docs.append({
                "text": text,
                "page": page_num + 1,
                "source": file_path
            })

    return docs
