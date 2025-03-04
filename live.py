import io
import pytesseract
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from PIL import Image, ExifTags

app = FastAPI()

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

async def process_images(files):
    """Process images directly from memory without saving to disk."""
    data_list = []
    
    for file in files:
        try:
            image = Image.open(io.BytesIO(await file.read()))
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

@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    if not files:
        return JSONResponse({"error": "No files uploaded."})

    try:
        df, report_file = await process_images(files)
        if df.empty:
            return JSONResponse({"error": "No valid images found in the uploaded files."})

        return JSONResponse({
            "success": "Images processed successfully.",
            "tables": [df.to_html(classes='table table-bordered', index=False)]
        })
    except Exception as e:
        return JSONResponse({"error": f"An error occurred: {e}"})

@app.post("/api/download")
async def download(files: list[UploadFile] = File(...)):
    """Allow downloading the generated Excel report without saving it."""
    try:
        if not files:
            return JSONResponse({"error": "No files uploaded."})

        _, report_file = await process_images(files)
        today_date = datetime.today().strftime('%Y-%m-%d')

        return StreamingResponse(
            io.BytesIO(report_file.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="scanned_report_{today_date}.xlsx"'}
        )
    except Exception as e:
        return JSONResponse({"error": f"Error generating file: {e}"})

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <h2>Upload Images for Processing</h2>
    <form action="/api/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="files" multiple>
        <button type="submit">Upload</button>
    </form>
    """

