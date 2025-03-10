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

import pytesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)

# Load environment variables
if os.getenv("VERCEL"):
    print("Running on Vercel, using environment variables.")
else:
    load_dotenv()  # Load .env for local development

# Function to download image from Cloudinary and convert it to OpenCV format
def url_to_image(url):
    response = requests.get(url, stream=True)
    if response.status_code == 200:
        image_array = np.asarray(bytearray(response.raw.read()), dtype=np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)  # Convert to grayscale
    return None

# Function to extract barcode text using Tesseract OCR
def extract_text_under_barcode(image_url):
    """Extract only the alphanumeric text appearing directly under the barcode."""
    image = url_to_image(image_url)
    if image is None:
        return "Error loading image"

    # Preprocessing: Increase contrast and threshold
    image = cv2.GaussianBlur(image, (5, 5), 0)  # Reduce noise
    _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # Binarization

    # Extract text using Tesseract OCR
    extracted_texts = pytesseract.image_to_string(image, config="--psm 6")
    
    # Filter only alphanumeric text (barcode format)
    extracted_code = ""
    max_y = float('-inf')
    
    for line in extracted_texts.split("\n"):
        text = re.sub(r'[^a-zA-Z0-9]', '', line.strip())  # Keep only alphanumeric text
        if 8 <= len(text) <= 30:
            extracted_code = text
    
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
    
    df.to_excel(excel_buffer, index=False)
    excel_buffer.seek(0)
    return data_list, excel_buffer

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
            data_list, excel_buffer = process_images(image_urls)
            if not data_list:
                return jsonify({"error": "No barcodes detected in the uploaded images."})

            processed_excel_buffer = excel_buffer

            return jsonify({
                "success": "Images processed successfully.",
                "tables": pd.DataFrame(data_list).to_html(classes='table table-bordered', index=False),
                "download_url": "/download"
            })
        except Exception as e:
            print(f"Processing error: {e}")
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
    port = int(os.environ.get("PORT", 5000))  # Render assigns a dynamic port
    app.run(host="0.0.0.0", port=port)



print("Checking Tesseract installation...")
os.system("which tesseract")
os.system("tesseract --version")



