from flask import Flask, render_template, request, send_file, jsonify
import os
import cv2
import numpy as np
from paddleocr import PaddleOCR
import pandas as pd
from io import BytesIO
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
import re
import requests
import openpyxl
from openpyxl.styles import Alignment

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Initialize PaddleOCR reader
ocr_reader = PaddleOCR(use_angle_cls=True, lang='en')

# Function to download image from Cloudinary and convert it to OpenCV format
def url_to_image(url):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        image_array = np.asarray(bytearray(response.raw.read()), dtype=np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)  # Convert to grayscale
    return None

# Function to extract barcode text using PaddleOCR
def extract_text_under_barcode(image_url):
    """Extract only the alphanumeric text appearing directly under the barcode using PaddleOCR."""
    image = url_to_image(image_url)
    if image is None:
        return "Error loading image"

    # Preprocessing: Increase contrast and threshold
    image = cv2.GaussianBlur(image, (5, 5), 0)  # Reduce noise
    _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # Binarization

    # Extract text using PaddleOCR
    result = ocr_reader.ocr(image, cls=True)

    # Extract and filter alphanumeric text
    extracted_code = ""
    for line in result:
        for word_info in line:
            text = word_info[1][0]  # Extract recognized text
            cleaned_text = re.sub(r'[^a-zA-Z0-9]', '', text.strip())  # Keep only alphanumeric text
            if 8 <= len(cleaned_text) <= 30:
                extracted_code = cleaned_text

    return extracted_code or "No barcode detected"

def generate_excel(data_list):
    """Generate and return an Excel file with hyperlinks."""
    df = pd.DataFrame(data_list, columns=["Image URL", "Extracted Code"])
    
    # Save DataFrame to an Excel buffer
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    
    # Load workbook for modifications
    excel_buffer.seek(0)
    wb = openpyxl.load_workbook(excel_buffer)
    ws = wb.active

    # Convert image URLs to clickable hyperlinks in Excel
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):  
        cell = row[0]  # First column
        cell.value = f'=HYPERLINK("{cell.value}", "{cell.value}")'

    # Save changes to a new buffer
    new_excel_buffer = BytesIO()
    wb.save(new_excel_buffer)
    new_excel_buffer.seek(0)

    return new_excel_buffer  # Return processed Excel file

def generate_html_table(data_list):
    """Generate HTML table with clickable links."""
    html_table = '<table class="table table-striped"><thead><tr><th>Image</th><th>Extracted Code</th></tr></thead><tbody>'
    for data in data_list:
        html_table += f'<tr><td><a href="{data["Image URL"]}" target="_blank">{data["Image URL"]}</a></td><td>{data["Extracted Code"]}</td></tr>'
    html_table += '</tbody></table>'
    return html_table

processed_excel_buffer = None  # Store latest processed Excel file

@app.route("/", methods=["GET", "POST"])
def index():
    global processed_excel_buffer
    if request.method == "POST":
        uploaded_files = request.files.getlist("images")

        if not uploaded_files or all(file.filename == "" for file in uploaded_files):
            return jsonify({"error": "No valid files uploaded."})

        image_urls = []
        for file in uploaded_files:
            if file and file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                try:
                    upload_result = cloudinary.uploader.upload(file)
                    image_urls.append(upload_result["secure_url"])
                except Exception as e:
                    return jsonify({"error": "Cloudinary upload failed.", "details": str(e)})
            else:
                return jsonify({"error": "Only PNG, JPG, JPEG files are allowed."})

        if not image_urls:
            return jsonify({"error": "No valid images found in the uploaded files."})

        try:
            data_list = [{"Image URL": url, "Extracted Code": extract_text_under_barcode(url)} for url in image_urls]

            if not data_list:
                return jsonify({"error": "No barcodes detected in the uploaded images."})

            processed_excel_buffer = generate_excel(data_list)  # Store Excel file
            table_html = generate_html_table(data_list)  # Generate HTML table

            return jsonify({
                "success": "Images processed successfully.",
                "table_html": table_html,
                "download_url": "/download"
            })
        except Exception as e:
            return jsonify({"error": f"An error occurred: {e}"})
    
    return render_template("index.html")

@app.route("/download")
def download():
    """Download the generated Excel file."""
    global processed_excel_buffer
    if not processed_excel_buffer:
        return jsonify({"error": "No processed data available for download."})

    return send_file(processed_excel_buffer, download_name="barcode_extraction_report.xlsx", as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port, debug=True)
