import requests
import PyPDF2
import io

# URL of the PDF file
pdf_url = "https://resources.workable.com/wp-content/uploads/2017/09/Employee-Handbook.pdf"

# Download the PDF file
response = requests.get(pdf_url)
response.raise_for_status()  # Ensure the request was successful

# Create a BytesIO object from the PDF content
pdf_bytes = io.BytesIO(response.content)

# Read the PDF using PyPDF2
pdf_reader = PyPDF2.PdfReader(pdf_bytes)
extracted_text = ""

# Extract text from each page
for page in pdf_reader.pages:
    page_text = page.extract_text()
    if page_text:
        extracted_text += page_text + "\n"

# Save the extracted text to a file (handbook.txt)
with open("handbook.txt", "w", encoding="utf-8") as f:
    f.write(extracted_text)

print("Text extraction complete. The handbook has been saved to handbook.txt")
