# OCR Extractor

## Overview
OCR Extractor is an advanced image processing tool designed to extract barcodes and metadata from images. It leverages **OpenCV**, **Tesseract OCR**, and **Pyzbar** to accurately scan barcodes, retrieve product details, and generate structured Excel reports. The project is optimized for handling bulk images efficiently.

## Features
- **Automated Barcode Scanning**: Extracts barcode data from images using OCR and Pyzbar.
- **Metadata Extraction**: Retrieves image metadata such as author and timestamp.
- **Bulk Processing**: Supports batch processing of images stored in designated folders.
- **Dynamic Excel Report Generation**: Saves extracted data into structured Excel sheets.
- **Versioned Reports**: Auto-generates versioned Excel reports (`v1.0`, `v2.0`, etc.).
- **Sorted Data**: Organizes images by timestamp and filename.
- **Scans Multiple Directories**: Supports scanning from multiple folders (`images` & `boxes`).

## Installation
### 1️. Create and Activate Virtual Environment
```bash
cd "D:\Projects\OCR Extractor"
python -m venv ocr_env
oct_env\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

## Folder Structure
```
D:\Projects\OCR Extractor
│── images                # Contains images with barcodes
│── boxes                 # Additional image folder
│── ocr_env               # Virtual environment
│── barcode_scanner.py    # Main Python script
│── requirements.txt      # List of dependencies
│── README.md             # Project documentation
```

## How to Use
### 1️. Run the Script
```bash
python barcode_scanner.py
```

### 2️. Output
- The extracted barcode data and metadata are saved in an **Excel file** inside `D:\Projects\OCR Extractor`.
- Files are named dynamically based on the date & version:
  ```
  scanned_products_2025-02-28_v1.0.xlsx
  scanned_boxes_2025-02-28_v1.0.xlsx
  ```

## Dependencies
- [Python 3.10+](https://www.python.org/)
- [OpenCV](https://opencv.org/)
- [Pandas](https://pandas.pydata.org/)
- [Pytesseract (Tesseract OCR)](https://github.com/madmaze/pytesseract)
- [Pillow](https://pillow.readthedocs.io/)
- [OpenPyXL](https://openpyxl.readthedocs.io/en/stable/)
- [Pyzbar](https://github.com/NaturalHistoryMuseum/pyzbar)

