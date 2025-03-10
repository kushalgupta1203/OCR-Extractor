from flask import Flask, render_template, request, send_file, jsonify
import os
import numpy as np
import pandas as pd
from io import BytesIO
import cloudinary.uploader
import requests
import re
from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Font

app = Flask(__name__)

# Load environment variables
if not os.getenv("VERCEL"):
    load_dotenv()  # Load .env for local development

OCR_API_KEY = os.getenv("OCR_API_KEY")
OCR_API_URL = "https://api.ocr.space/parse/image"  # Change this if using a different API

# Global variable to store processed data
processed_data_list = []

def extract_text_under_barcode(image_url):
    """Extract text using an OCR API."""
    if not OCR_API_KEY:
        return "OCR API Key is missing"

    try:
        payload = {
            "apikey": OCR_API_KEY,
            "url": image_url,
            "language": "eng",
            "isOverlayRequired": False
        }
        response = requests.post(OCR_API_URL, data=payload)
        result = response.json()

        # Extract text from API response
        extracted_text = ""
        if "ParsedResults" in result:
            for item in result["ParsedResults"]:
                extracted_text += item["ParsedText"] + "\n"

        # Extract only alphanumeric barcode-like text
        extracted_code = ""
        for line in extracted_text.split("\n"):
            cleaned_text = re.sub(r'[^a-zA-Z0-9]', '', line.strip())  # Keep only alphanumeric characters
            if 8 <= len(cleaned_text) <= 30:  # Barcode-like length
                extracted_code = cleaned_text

        return extracted_code or "No barcode detected"

    except Exception as e:
        return f"OCR API Error: {str(e)}"

def process_images(image_urls):
    """Extract barcode text and store data for rendering & Excel generation."""
    global processed_data_list
    processed_data_list = []  # Reset data list

    for image_url in image_urls:
        extracted_code = extract_text_under_barcode(image_url)
        print(f"Processing {image_url} -> Extracted Code: {extracted_code}")  # Debugging

        processed_data_list.append({
            "Image URL": image_url,
            "Extracted Code": extracted_code if extracted_code else "No code detected"
        })

def generate_excel():
    """Generate Excel with proper hyperlink formatting."""
    if not processed_data_list:
        return None

    try:
        wb = Workbook()
        ws = wb.active
        ws.append(["Image URL", "Extracted Code"])
        
        # Add data with hyperlink formatting
        for data in processed_data_list:
            row = [
                data['Image URL'],
                data['Extracted Code']
            ]
            ws.append(row)
            
            # Create hyperlink for image URL
            cell = ws.cell(row=ws.max_row, column=1)
            cell.hyperlink = data['Image URL']
            cell.font = Font(color="0000FF", underline="single")

        # Set column widths
        ws.column_dimensions['A'].width = 60
        ws.column_dimensions['B'].width = 30

        excel_buffer = BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer

    except Exception as e:
        print(f"Excel generation error: {str(e)}")
        return None

def generate_html_table():
    """Generate an HTML table with clickable thumbnails and codes."""
    if not processed_data_list:
        return "<p>No data available.</p>"

    html_table = '''<table class="table table-striped">
        <thead><tr><th>Image</th><th>Extracted Code</th></tr></thead>
        <tbody>'''
    
    for data in processed_data_list:
        html_table += f'''
        <tr>
            <td>
                <a href="{data['Image URL']}" target="_blank" class="image-link">
                    <img src="{data['Image URL']}" class="thumbnail">
                </a>
            </td>
            <td>
                <a href="{data['Image URL']}" target="_blank" class="code-link">
                    {data['Extracted Code']}
                </a>
            </td>
        </tr>'''
    html_table += '</tbody></table>'
    
    return html_table

@app.route("/", methods=["GET", "POST"])
def index():
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
            process_images(image_urls)
            return jsonify({
                "success": "Images processed successfully.",
                "table_html": generate_html_table(),
                "download_url": "/download"
            })
        except Exception as e:
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
