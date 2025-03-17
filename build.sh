#!/bin/bash
wget https://github.com/tesseract-ocr/tesseract/releases/download/5.3.0/tesseract-5.3.0-linux-x86_64.tar.gz
tar -xvzf tesseract-5.3.0-linux-x86_64.tar.gz
mv tesseract-5.3.0 /opt/tesseract
export PATH="/opt/tesseract/bin:$PATH"
