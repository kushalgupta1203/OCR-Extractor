import io
from flask import Flask, render_template, request, send_file, jsonify
import pytesseract
import pandas as pd
from datetime import datetime
from PIL import Image, ExifTags

app = Flask(__name__)

def extract_metadata(image):
    """Extract metadata like author and taken time from an image."""
    try:
        exif_data = image._getexif()
        if not exif_data:
            return "Unknown", "Unknown"
        metadata = {ExifTags.TAGS.get(tag_id, tag_id): value for tag_id, value in exif_data.items()}
        return metadata.get("Artist", "Unknown"), metadata.get("DateTime", "Unknown")
    except Exception:
        return "Unknown", "Unknown"

def process_images(uploaded_files):
    """Process images directly from memory without saving to disk."""
    data_list = []
    
    for file in uploaded_files:
        try:
            image = Image.open(file)
            barcode_data = pytesseract.image_to_string(image.convert("L")).strip()
            author, taken_time = extract_metadata(image)
            data_list.append({
                "Image": file.filename,
                "Barcode": barcode_data if barcode_data else "Not Detected",
                "Author": author,
                "Taken Time": taken_time
            })
        except Exception as e:
            print(f"Error processing {file.filename}: {e}")

    df = pd.DataFrame(data_list)
    
    # Generate Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    output.seek(0)

    return df, output

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_files = request.files.getlist("images")
        if not uploaded_files or all(file.filename == "" for file in uploaded_files):
            return jsonify({"error": "No files uploaded."})

        try:
            df, report_file = process_images(uploaded_files)
            if df.empty:
                return jsonify({"error": "No valid images found in the uploaded files."})

            return jsonify({
                "success": "Images processed successfully.",
                "tables": [df.to_html(classes='table table-bordered', index=False)]
            })
        except Exception as e:
            return jsonify({"error": f"An error occurred: {e}"})

    return render_template("index.html")

@app.route("/api/download", methods=["POST"])
def download():
    """Allow downloading the generated Excel report without saving it."""
    try:
        uploaded_files = request.files.getlist("images")
        if not uploaded_files:
            return jsonify({"error": "No files uploaded."})

        _, report_file = process_images(uploaded_files)
        today_date = datetime.today().strftime('%Y-%m-%d')

        return send_file(report_file, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         as_attachment=True, download_name=f"scanned_report_{today_date}.xlsx")
    except Exception as e:
        return f"Error generating file: {e}", 500

if __name__ == "__main__":
    app.run(debug=True)
