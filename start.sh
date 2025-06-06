#!/bin/bash
apt-get update && apt-get install -y tesseract-ocr
python3 main.py
