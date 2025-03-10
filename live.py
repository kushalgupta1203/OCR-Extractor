from flask import Flask, render_template, request, send_file, jsonify
import os
import cv2
import numpy as np
import pytesseract
import pandas as pd
from io import BytesIO
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
import re
import requests

app = Flask(__name__)

# Load environment variables
if os.getenv("VERCEL"):
    print("Running on Vercel, using environment variables.")
else:
    load_dotenv()  # Load .env for local development

# Set Tesseract Path for Render (if needed)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# Global variable to store processed data
processed_data_list = []

def url_to_image(url):
    """Download image from URL and convert to OpenCV format."""
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        image_array = np.asarray(bytearray(response.raw.read()), dtype=np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)  # Convert to grayscale
    return None

def extract_text_under_barcode(image_url):
    """Extract alphanumeric text appearing under the barcode using Tesseract OCR."""
    image = url_to_image(image_url)
    if image is None:
        return "Error loading image"

    # Resize to standard dimensions (to handle large images)
    if image.shape[0] > 1000 or image.shape[1] > 1000:
        image = cv2.resize(image, (1000, 1000))

    # Preprocessing: Increase contrast and threshold
    image = cv2.GaussianBlur(image, (5, 5), 0)  # Reduce noise
    _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # Binarization

    # Extract text using Tesseract OCR
    extracted_text = pytesseract.image_to_string(image, config='--psm 6')  # PSM 6 is good for block text

    # Extract and filter alphanumeric text (barcode text usually has a specific format)
    extracted_code = ""
    for line in extracted_text.split("\n"):
        cleaned_text = re.sub(r'[^a-zA-Z0-9]', '', line.strip())  # Keep only alphanumeric text
        if 8 <= len(cleaned_text) <= 30:  # Barcode range check
            extracted_code = cleaned_text

    return extracted_code or "No barcode detected"

def process_images(image_urls):
    """Extract barcode text and store data for rendering & Excel generation."""
    global processed_data_list
    processed_data_list = []  # Reset data list

    for image_url in image_urls:
        try:
            extracted_code = extract_text_under_barcode(image_url)
            print(f"Processing {image_url} -> Extracted Code: {extracted_code}")  # Debugging

            processed_data_list.append({
                "Image URL": image_url,
                "Extracted Code": extracted_code if extracted_code else "No code detected"
            })

        except Exception as e:
            print(f"Error processing image {image_url}: {e}")
            continue

def generate_excel():
    """Generate an Excel file dynamically (avoiding large memory allocation)."""
    if not processed_data_list:
        return None

    df = pd.DataFrame(processed_data_list, columns=["Image URL", "Extracted Code"])
    excel_buffer = BytesIO()
    df.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)

    return excel_buffer

def generate_html_table():
    """Generate HTML table with clickable links for rendering."""
    if not processed_data_list:
        return "<p>No data available.</p>"

    html_table = '<table class="table table-striped"><thead><tr><th>Image</th><th>Extracted Code</th></tr></thead><tbody>'
    for data in processed_data_list:
        html_table += f'<tr><td><a href="{data["Image URL"]}" target="_blank">{data["Image URL"]}</a></td><td>{data["Extracted Code"]}</td></tr>'
    html_table += '</tbody></table>'

    return html_table

@app.route("/", methods=["GET", "POST"])
def index():
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
            process_images(image_urls)

            return jsonify({
                "success": "Images processed successfully.",
                "table_html": generate_html_table(),
                "download_url": "/download"
            })
        except Exception as e:
            print(f"Processing error: {e}")
            return jsonify({"error": f"An error occurred: {e}"})

    return render_template("index.html")

@app.route("/download")
def download():
    """Generate and send Excel file dynamically."""
    excel_buffer = generate_excel()
    if not excel_buffer:
        return jsonify({"error": "No processed data available for download."})

    return send_file(excel_buffer, download_name="barcode_extraction_report.xlsx", as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host="0.0.0.0", port=port, debug=True)
