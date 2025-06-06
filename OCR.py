import cv2
import pytesseract
import re
import logging

# === OCR Functions ===

def preprocess_and_ocr(roi):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    clahe_img = clahe.apply(gray)
    blurred = cv2.GaussianBlur(clahe_img, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(binary, config=custom_config)
    return text

def extract_addresses_from_image(image_path):
    """Run OCR on the image and extract addresses using heuristics."""
    image = cv2.imread(image_path)
    if image is None:
        return []
    
    height, width = image.shape[:2]
    # Process top and bottom halves of the image
    roi_top = image[0:int(height * 0.5), 0:width]
    roi_bottom = image[int(height * 0.5):height, 0:width]
    
    text_top = preprocess_and_ocr(roi_top)
    text_bottom = preprocess_and_ocr(roi_bottom)
    
    combined_text = text_top + "\n" + text_bottom
    logging.info("Combined OCR Text:\n%s", combined_text)
    
    # Post-Processing: Extract addresses using heuristics
    lines = combined_text.splitlines()
    addresses = []
    current_addr = ""
    
    # Define patterns for start and end markers and words to ignore
    start_pattern = re.compile(r'[A-Za-z0-9#-]+\s+.*(?:Road|Rd(?:\s?[A-Za-z]+)?|View|Avenue|Ave|Street|St\.|Blk|Drive|Dr\.?)', re.IGNORECASE)
    end_pattern = re.compile(r'(Singapore|SG)', re.IGNORECASE)
    ignore_pattern = re.compile(r'(Delivery|Scheduled|Parcels|Itinerary)', re.IGNORECASE)
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if start_pattern.search(line):
            if current_addr:
                addresses.append(current_addr)
            current_addr = line
        elif current_addr:
            if end_pattern.search(line):
                current_addr += " " + line
                addresses.append(current_addr)
                current_addr = ""
            elif not ignore_pattern.search(line):
                current_addr += " " + line
            else:
                addresses.append(current_addr)
                current_addr = ""
    if current_addr:
        addresses.append(current_addr)
    
    # Preserve only the street number and street name
    street_pattern = re.compile(r'([A-Za-z0-9#-]+\s+.*(?:Road|Rd(?:\s?[A-Za-z]+)?|View|Avenue|Ave|Street|St\.|Drive|Dr\.?))', re.IGNORECASE)
    preserved_streets = []
    for addr in addresses:
        match = street_pattern.search(addr)
        if match:
            street = match.group(1).strip()
            preserved_streets.append(street)
    
    return preserved_streets
