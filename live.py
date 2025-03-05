from flask import Flask, render_template, request, send_file, jsonify
import os
import easyocr
import pandas as pd
from datetime import datetime
from io import BytesIO
import barcode
from barcode.writer import ImageWriter
from openpyxl.drawing.image import Image as XLImage
import re
import cloudinary
import cloudinary.uploader
import cloudinary.api
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Cloudinary Configuration from .env
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

# Initialize EasyOCR reader
reader = easyocr.Reader(['en'])

def generate_barcode(data):
    """Generate barcode image and return as BytesIO object."""
    try:
        if not data or len(data) < 8:
            return None  # Avoid generating barcode for invalid data
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(data, writer=ImageWriter())
        barcode_img = BytesIO()
        barcode_instance.write(barcode_img)
        barcode_img.seek(0)
        return barcode_img
    except Exception:
        return None

def extract_text_under_barcode(image_url):
    """Extract only the alphanumeric text that appears directly under the barcode from Cloudinary image URL."""
    extracted_texts = reader.readtext(image_url, detail=1)
    extracted_code = ""
    max_y = float('-inf')
    
    for bbox, text, _ in extracted_texts:
        text = re.sub(r'[^a-zA-Z0-9]', '', text)  # Remove symbols, keep only alphanumeric
        (x_min, y_min, x_max, y_max) = bbox[0][1], bbox[2][1], bbox[0][0], bbox[2][0]
        
        if y_min > max_y and 8 <= len(text) <= 30:  # Ensure text is below barcode and within length constraints
            max_y = y_min
            extracted_code = text
    
    return extracted_code

def process_images(image_urls):
    """Extract text under barcode and generate barcode image in Excel using Cloudinary URLs."""
    data_list = []
    
    for image_url in image_urls:
        try:
            extracted_code = extract_text_under_barcode(image_url)
            barcode_img_data = generate_barcode(extracted_code)
            data_list.append({
                "Image URL": image_url,
                "Extracted Code": extracted_code if extracted_code else "No code detected",
                "Barcode Image": barcode_img_data
            })
        except Exception:
            continue

    df = pd.DataFrame(data_list)
    today_date = datetime.today().strftime('%Y-%m-%d')
    output_excel = f"barcode_extraction_report_{today_date}.xlsx"

    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        df.drop(columns=["Barcode Image"], inplace=True)  # Remove image column for main sheet
        df.to_excel(writer, index=False, sheet_name="Extracted Data")
        workbook = writer.book
        worksheet = writer.sheets["Extracted Data"]

        for index, img_data in enumerate(data_list):
            if img_data["Barcode Image"]:
                img_io = img_data["Barcode Image"]
                excel_img = XLImage(img_io)
                excel_img.width = 100  # Adjusted barcode size
                excel_img.height = 30
                cell_position = f"C{index + 2}"  # Barcode image placed in a new column
                worksheet.add_image(excel_img, cell_position)

    return df, output_excel

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_files = request.files.getlist("images")
        if not uploaded_files or all(file.filename == "" for file in uploaded_files):
            return jsonify({"error": "No files uploaded."})

        image_urls = []
        
        for file in uploaded_files:
            if file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
                upload_result = cloudinary.uploader.upload(file)
                image_url = upload_result["secure_url"]
                image_urls.append(image_url)
            else:
                return jsonify({"error": "Only PNG, JPG, JPEG files are allowed."})

        try:
            df, report_path = process_images(image_urls)
            if df.empty:
                return jsonify({"error": "No valid images found in the uploaded files."})
            return jsonify({
                "success": "Images processed successfully.",
                "tables": [df.to_html(classes='table table-bordered', index=False)],
                "codes": df["Extracted Code"].tolist(),  # Show generated codes on result screen
                "uploaded_images": image_urls  # Return Cloudinary URLs
            })
        except Exception as e:
            return jsonify({"error": f"An error occurred: {e}"})

    return render_template("index.html")

@app.route("/download")
def download():
    today_date = datetime.today().strftime('%Y-%m-%d')
    report_path = f"barcode_extraction_report_{today_date}.xlsx"
    if not os.path.exists(report_path):
        return "File not found.", 404
    return send_file(report_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
