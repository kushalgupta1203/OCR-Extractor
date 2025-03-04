import cv2
import os
import pandas as pd
import pytesseract
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS

# Set path for Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Folder paths
image_folder = r"D:\Projects\OCR Extractor\images"
box_folder = r"D:\Projects\OCR Extractor\boxes"
output_folder = r"D:\Projects\OCR Extractor"

def get_latest_version(folder_path, base_name):
    """Check for existing versions and return the next available version number."""
    existing_files = [f for f in os.listdir(folder_path) if f.startswith(base_name)]
    versions = [int(f.split('_v')[-1].split('.')[0]) for f in existing_files if '_v' in f]
    next_version = max(versions) + 1 if versions else 1
    return next_version

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
    except Exception as e:
        return "Unknown", "Unknown"

def process_images(folder_path, base_name):
    """Process images to extract barcodes and metadata, save to a versioned Excel file."""
    data_list = []
    
    for filename in sorted(os.listdir(folder_path)):  # Sort filenames alphabetically
        if filename.lower().endswith((".png", ".jpg", ".jpeg")):
            image_path = os.path.join(folder_path, filename)
            image = cv2.imread(image_path)

            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Extract barcode using pytesseract
            barcode_data = pytesseract.image_to_string(gray).strip()

            # Extract metadata
            author, taken_time = extract_metadata(image_path)

            data_list.append({
                "Image": filename,
                "Barcode": barcode_data if barcode_data else "Not Detected",
                "Author": author,
                "Taken Time": taken_time
            })

    # Convert list to DataFrame
    df = pd.DataFrame(data_list)

    # Sort by date, then alphabetically if same timestamp
    df.sort_values(by=["Taken Time", "Image"], ascending=True, inplace=True)

    # Generate filename with date & version
    today_date = datetime.today().strftime('%Y-%m-%d')
    next_version = get_latest_version(output_folder, f"{base_name}_{today_date}")
    output_excel = os.path.join(output_folder, f"{base_name}_{today_date}_v{next_version}.0.xlsx")

    # Save to Excel
    df.to_excel(output_excel, index=False)
    print(f"Excel file saved at: {output_excel}")

# Process both folders
process_images(image_folder, "scanned_products")
process_images(box_folder, "scanned_boxes")
