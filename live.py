from flask import Flask, render_template, request, send_file, jsonify
import os
import pytesseract
import pandas as pd
from datetime import datetime
from PIL import Image, ExifTags

app = Flask(__name__)

# Set path for Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

# Define universal upload path
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
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

def process_images(image_folder):
    """Process images to extract barcode data and metadata."""
    data_list = []
    for filename in sorted(os.listdir(image_folder)):
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            image_path = os.path.join(image_folder, filename)
            try:
                barcode_data = pytesseract.image_to_string(Image.open(image_path).convert("L")).strip()
                author, taken_time = extract_metadata(image_path)
                data_list.append({
                    "Image": filename,
                    "Barcode": barcode_data if barcode_data else "Not Detected",
                    "Author": author,
                    "Taken Time": taken_time
                })
            except Exception:
                continue
    df = pd.DataFrame(data_list)
    today_date = datetime.today().strftime('%Y-%m-%d')
    output_excel = os.path.join(UPLOAD_FOLDER, f"scanned_report_{today_date}.xlsx")
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
    report_path = os.path.join(UPLOAD_FOLDER, f"scanned_report_{today_date}.xlsx")
    if not os.path.exists(report_path):
        return "File not found.", 404
    return send_file(report_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
