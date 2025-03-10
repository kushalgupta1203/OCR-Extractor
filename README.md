https://ocr-extractor.onrender.com/

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
