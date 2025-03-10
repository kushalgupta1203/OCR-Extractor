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

def process_images(image_urls):
    """Extract barcode text and save to Excel."""
    data_list = []
    excel_buffer = BytesIO()
    df = pd.DataFrame(columns=["Image URL", "Extracted Code"])
    
    for image_url in image_urls:
        try:
            extracted_code = extract_text_under_barcode(image_url)
            print(f"Processing {image_url} -> Extracted Code: {extracted_code}")  # Debugging

            data_list.append({
                "Image URL": image_url,
                "Extracted Code": extracted_code if extracted_code else "No code detected"
            })

            df = pd.concat([df, pd.DataFrame([[image_url, extracted_code]], columns=["Image URL", "Extracted Code"])], ignore_index=True)

        except Exception as e:
            print(f"Error processing image {image_url}: {e}")
            continue
    
   # Convert "Image URL" to clickable links for HTML table
    df_html = df.copy()
    df_html['Image URL'] = df_html['Image URL'].apply(lambda x: f'<a href="{x}" target="_blank">{x}</a>')
    
    # Generate HTML table
    table_html = df_html.to_html(escape=False, classes='table table-striped', index=False, border=0)

    # Save to Excel
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    
    # Load the Excel file to adjust alignment and make URLs clickable
    wb = openpyxl.load_workbook(filename=BytesIO(excel_buffer.read()))
    ws = wb.active
    
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):  # Skip header row
        cell = row[0]  # First column
        cell.value = f'=HYPERLINK("{cell.value}", "{cell.value}")'  # Make URL clickable
       # cell.alignment = Alignment(horizontal='left')  ## REMOVE THIS LINE
    
    # Save changes back to BytesIO
    excel_buffer.seek(0)
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    return data_list, excel_buffer, table_html

processed_excel_buffer = None  # Store latest processed file

@app.route("/", methods=["GET", "POST"])
def index():
    global processed_excel_buffer
    if request.method == "POST":
        uploaded_files = request.files.getlist("images")
        
        # Debugging: Check if files are received
        if not uploaded_files or all(file.filename == "" for file in uploaded_files):
            print("No files received or empty filenames.")
            return jsonify({"error": "No valid files uploaded."})

        image_urls = []
        for file in uploaded_files:
            if file and file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                try:
                    upload_result = cloudinary.uploader.upload(file)
                    image_urls.append(upload_result["secure_url"])
                except Exception as e:
                    print(f"Cloudinary upload failed: {e}")
                    return jsonify({"error": "Cloudinary upload failed.", "details": str(e)})
            else:
                print(f"Invalid file format: {file.filename}")
                return jsonify({"error": "Only PNG, JPG, JPEG files are allowed."})

        if not image_urls:
            return jsonify({"error": "No valid images found in the uploaded files."})

        try:
            data_list, excel_buffer, table_html = process_images(image_urls)
            if not data_list:
                return jsonify({"error": "No barcodes detected in the uploaded images."})

            processed_excel_buffer = excel_buffer

            return jsonify({
                "success": "Images processed successfully.",
                "table_html": table_html,
                "download_url": "/download"
            })
        except Exception as e:
            print(f"Processing error: {e}")
            return jsonify({"error": f"An error occurred: {e}"})
    
    return render_template("local.html")

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
