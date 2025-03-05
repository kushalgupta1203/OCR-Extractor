from flask import Flask, render_template, request, send_file, jsonify
import os
import pytesseract
import pandas as pd
from datetime import datetime
from PIL import Image, ExifTags
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)

# Set path for Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# Define upload path
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def extract_metadata(image_path):
    """Extract metadata like author and taken time from image."""
    try:
        img = Image.open(image_path)
        exif_data = img._getexif()
        if not exif_data:
            return "Unknown", "Unknown"
        metadata = {ExifTags.TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}
        return metadata.get("Artist", "Unknown"), metadata.get("DateTime", "Unknown")
    except Exception:
        return "Unknown", "Unknown"

def generate_barcode(text, output_path):
    """Generate barcode image from extracted text."""
    try:
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(text, writer=ImageWriter())
        barcode_instance.save(output_path)
        return output_path + ".png"
    except Exception:
        return ""

def process_images(image_folder):
    """Extract text, metadata, and generate barcode for extracted text."""
    data_list = []
    for filename in sorted(os.listdir(image_folder)):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            image_path = os.path.join(image_folder, filename)
            try:
                extracted_text = pytesseract.image_to_string(Image.open(image_path)).strip()
                author, taken_time = extract_metadata(image_path)
                barcode_path = ""
                if extracted_text:
                    barcode_path = generate_barcode(extracted_text, os.path.join(UPLOAD_FOLDER, filename.split('.')[0]))
                data_list.append({
                    "Image": filename,
                    "Extracted Text": extracted_text if extracted_text else "No text detected",
                    "Barcode Image": barcode_path,
                    "Author": author,
                    "Taken Time": taken_time
                })
            except Exception:
                continue
    
    df = pd.DataFrame(data_list)
    today_date = datetime.today().strftime('%Y-%m-%d')
    output_excel = os.path.join(UPLOAD_FOLDER, f"text_extraction_report_{today_date}.xlsx")
    df.to_excel(output_excel, index=False, engine="openpyxl")
    return df, output_excel

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_files = request.files.getlist("images")
        if not uploaded_files or all(file.filename == "" for file in uploaded_files):
            return jsonify({"error": "No files uploaded."})

        # Clear old files
        for file in os.listdir(UPLOAD_FOLDER):
            os.remove(os.path.join(UPLOAD_FOLDER, file))

        # Save new images
        for file in uploaded_files:
            if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                file.save(os.path.join(UPLOAD_FOLDER, file.filename))
            else:
                return jsonify({"error": "Only PNG, JPG, JPEG files are allowed."})

        try:
            df, report_path = process_images(UPLOAD_FOLDER)
            if df.empty:
                return jsonify({"error": "No valid images found in the uploaded files."})
            return jsonify({
                "success": "Images processed successfully.",
                "tables": [df.to_html(classes='table table-bordered', index=False)]
            })
        except Exception as e:
            return jsonify({"error": f"An error occurred: {e}"})

    return render_template("index.html")

@app.route("/download")
def download():
    today_date = datetime.today().strftime('%Y-%m-%d')
    report_path = os.path.join(UPLOAD_FOLDER, f"text_extraction_report_{today_date}.xlsx")
    if not os.path.exists(report_path):
        return "File not found.", 404
    return send_file(report_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
