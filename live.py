from flask import Flask, render_template, request, send_file, jsonify
import os
import easyocr
import pandas as pd
from io import BytesIO
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv
import re

app = Flask(__name__)

# Load environment variables
if os.getenv("VERCEL"):
    print("Running on Vercel, using environment variables.")
else:
    load_dotenv()  # Load .env for local development

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

def extract_text_under_barcode(image_url):
    """Extract only the alphanumeric text that appears directly under the barcode from Cloudinary image URL."""
    extracted_texts = reader.readtext(image_url, detail=1)
    
    extracted_code = ""
    max_y = float('-inf')
    
    for bbox, text, _ in extracted_texts:
        text = re.sub(r'[^a-zA-Z0-9]', '', text)  # Keep only alphanumeric
        (x_min, y_min, x_max, y_max) = bbox[0][1], bbox[2][1], bbox[0][0], bbox[2][0]
        
        if y_min > max_y and 8 <= len(text) <= 30:
            max_y = y_min
            extracted_code = text
    
    return extracted_code

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


