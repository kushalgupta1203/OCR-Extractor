import os
import re
import pytesseract
from PIL import Image
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font
import streamlit as st

# Set up Tesseract executable path (adjust this path based on your system)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Supported image formats
SUPPORTED_FORMATS = ["png", "jpg", "jpeg", "tiff", "bmp"]

def extract_text_from_image(image):
    """Extract text from an image using pytesseract."""
    try:
        text = pytesseract.image_to_string(image, lang='eng')
        cleaned_text = re.sub(r'[^A-Z0-9]', '', text.upper())
        if 8 <= len(cleaned_text) <= 30:
            return cleaned_text
        return "No valid code found"
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return "OCR processing failed"

def process_images(files):
    """Process uploaded images and extract text."""
    results = []
    for file in files:
        try:
            # Open the image using PIL
            image = Image.open(file)
            extracted_text = extract_text_from_image(image)
            results.append({
                "Filename": file.name,
                "Extracted Code": extracted_text
            })
        except Exception as e:
            st.error(f"Error processing file {file.name}: {str(e)}")
            results.append({
                "Filename": file.name,
                "Extracted Code": "Processing error"
            })
    return results

def generate_excel(results):
    """Generate an Excel file from the processed results."""
    wb = Workbook()
    ws = wb.active
    ws.append(["Filename", "Extracted Code"])

    for result in results:
        ws.append([result["Filename"], result["Extracted Code"]])

    ws.column_dimensions['A'].width = 40
    ws.column_dimensions['B'].width = 30

    excel_buffer = BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)

    return excel_buffer

# Streamlit App
st.title("OCR Extractor with Tesseract")

# Tabs for navigation
tab1, tab2, tab3 = st.tabs(["Instructions", "Upload Images", "Results"])

with tab1:
    st.header("How to Use")
    st.markdown("""
    1. Upload one or more image files (PNG, JPG, JPEG, TIFF, BMP).
    2. Process the images to extract codes.
    3. View the results in a table.
    4. Download the results as an Excel file.
    """)

with tab2:
    st.header("Upload Images")
    
    uploaded_files = st.file_uploader(
        "Upload image files (PNG, JPG, JPEG, TIFF, BMP)", 
        type=SUPPORTED_FORMATS, 
        accept_multiple_files=True
    )

    if uploaded_files:
        if st.button("Process Images"):
            with st.spinner("Processing images..."):
                results = process_images(uploaded_files)
                st.session_state["results"] = results

with tab3:
    st.header("Results")

    if "results" in st.session_state and st.session_state["results"]:
        results_table = st.session_state["results"]
        
        # Display results in a table format
        for result in results_table:
            st.write(f"**Filename:** {result['Filename']}")
            st.code(result["Extracted Code"])
        
        # Generate and download Excel report
        excel_file = generate_excel(results_table)
        
        st.download_button(
            label="Download Results as Excel",
            data=excel_file,
            file_name="ocr_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
