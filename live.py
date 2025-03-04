from flask import Flask, render_template, request, send_file, jsonify
import os
import cv2
import pandas as pd
import pytesseract
import time
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS

app = Flask(__name__)

# Set path for Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# Define universal upload path
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def extract_metadata(image_path):
    """Extract metadata like author and taken time from image."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        metadata = {}
        if exif_data:
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                metadata[tag_name] = value
        author = metadata.get("Artist", "Unknown")
        taken_time = metadata.get("DateTime", "Unknown")
        return author, taken_time
    except Exception:
        return "Unknown", "Unknown"

def process_images(image_folder):
    """Process images to extract barcode data and metadata."""
    start_time = time.time()
    data_list = []
    for filename in sorted(os.listdir(image_folder)):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            image_path = os.path.join(image_folder, filename)
            image = cv2.imread(image_path)
            if image is None:
                continue
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            barcode_data = pytesseract.image_to_string(gray).strip()
            author, taken_time = extract_metadata(image_path)
            data_list.append({
                "Image": filename,
                "Barcode": barcode_data if barcode_data else "Not Detected",
                "Author": author,
                "Taken Time": taken_time
            })
    df = pd.DataFrame(data_list)
    df.sort_values(by=["Taken Time", "Image"], ascending=True, inplace=True)
    today_date = datetime.today().strftime('%Y-%m-%d')
    output_excel = os.path.join(UPLOAD_FOLDER, f"scanned_report_{today_date}.xlsx")
    df.to_excel(output_excel, index=False)
    end_time = time.time()
    processing_time = round(end_time - start_time, 2)
    return df, output_excel, processing_time

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_files = request.files.getlist("images")
        if not uploaded_files or all(file.filename == "" for file in uploaded_files):
            return jsonify({"error": "No files uploaded."})
        else:
            for file in os.listdir(UPLOAD_FOLDER):
                os.remove(os.path.join(UPLOAD_FOLDER, file))
            for file in uploaded_files:
                if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
                    file.save(file_path)
                else:
                    return jsonify({"error": "Only PNG, JPG, JPEG files are allowed."})
            try:
                df, report_path, processing_time = process_images(UPLOAD_FOLDER)
                if df.empty:
                    return jsonify({"error": "No valid images found in the uploaded files."})
                else:
                    tables = [df.to_html(classes='table table-bordered', index=False)]
                    return jsonify({
                        "success": f"Images processed successfully in {processing_time} seconds.",
                        "tables": tables
                    })
            except Exception as e:
                return jsonify({"error": f"An error occurred during processing: {e}"})
    return render_template("index.html")

@app.route("/download")
def download():
    today_date = datetime.today().strftime('%Y-%m-%d')
    report_path = os.path.join(UPLOAD_FOLDER, f"scanned_report_{today_date}.xlsx")
    if not os.path.exists(report_path):
        return "File not found.", 404
    return send_file(report_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
