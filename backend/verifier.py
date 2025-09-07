import os
import re
import cv2
import numpy as np
from pdf2image import convert_from_path
from pdfminer.high_level import extract_text
import pytesseract
import pikepdf
from skimage.metrics import structural_similarity as ssim
from PIL import Image

# ---------- CONFIG ----------
CBSE_LOGO_PATH = 'cbselogo.png'      # Reference logo image
TEMPLATE_PATH = 'class12cbse.png'    # Reference template image

# ---------- STEP 1: Extract text ----------
def extract_pdf_text(pdf_path):
    try:
        text = extract_text(pdf_path)
        if text.strip():
            return text
    except Exception as e:
        print(f"PDF text extraction failed: {e}")
    return None

def ocr_image(image):
    return pytesseract.image_to_string(np.array(image))

# ---------- STEP 2: Convert PDF to images ----------
def pdf_to_images(pdf_path):
    try:
        return convert_from_path(pdf_path, dpi=300)
    except Exception as e:
        print(f"PDF to image conversion failed: {e}")
        return []

# ---------- STEP 3: Parse details ----------
def parse_details(text):
    # Clean text
    text = text.replace('\r', '\n').replace('\u00A0', ' ')
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    print(text)

    details = {
        "roll_no": None,
        "candidate_name": None,
        "mother_name": None,
        "father_name": None,
        "school_name": None,
        "subjects": {},
        "layout_issue": False,
        "font_issue": False,
    }

    # ---------- Extract candidate info ----------
    # Find index of last label
    labels = ["Roll No", "Candidate Name", "Mother's Name", "Father's Name", "School's Name"]
    last_label_idx = max((i for i, line in enumerate(lines) for lbl in labels if lbl.lower() in line.lower()), default=-1)

    # The next few lines are the values in order
    try:
        values = lines[last_label_idx+1:last_label_idx+6]
        details['roll_no'] = values[0] if len(values) > 0 else None
        details['candidate_name'] = values[1] if len(values) > 1 else None
        details['mother_name'] = values[2] if len(values) > 2 else None
        details['father_name'] = values[3] if len(values) > 3 else None
        details['school_name'] = values[4] if len(values) > 4 else None
    except Exception as e:
        details['layout_issue'] = True

    # ---------- Extract subjects dynamically ----------
    # Collect lines between first subject code/name and 'Result'
    subject_start_idx = next((i for i, line in enumerate(lines) if re.search(r'\bSUB CODE\b', line, re.IGNORECASE)), None)
    subject_end_idx = next((i for i, line in enumerate(lines) if re.search(r'\bResult\b', line, re.IGNORECASE)), None)

    if subject_start_idx is not None and subject_end_idx is not None and subject_start_idx < subject_end_idx:
        for line in lines[subject_start_idx+1:subject_end_idx]:
            # Skip headers like THEORY, POSITIONAL, GRADE
            if re.match(r'^(THEORY|POSITIONAL|GRADE|Prac|MARKS)$', line, re.IGNORECASE):
                continue
            if line.strip():  # Only non-empty lines
                details['subjects'][line.strip()] = "Present"

    # ---------- Font issue check ----------
    critical = ' '.join(filter(None, [
        details['roll_no'],
        details['candidate_name'],
        details['mother_name'],
        details['father_name'],
        details['school_name']
    ]))
    if re.search(r'[^a-zA-Z0-9\s.&]', critical):
        details['font_issue'] = True

    return details


# ---------- STEP 4: Metadata check ----------
def check_metadata(pdf_path):
    flags = []
    if not pdf_path.lower().endswith(".pdf"):
        return flags
    try:
        with pikepdf.open(pdf_path) as pdf:
            info = pdf.docinfo
            if '/Producer' in info:
                prod = str(info['/Producer'])
                if 'Photoshop' in prod or 'Adobe Illustrator' in prod:
                    flags.append(f'Edited with {prod}')
            if '/ModDate' in info:
                flags.append(f"Modified: {str(info['/ModDate'])}")
    except Exception as e:
        print(f"Metadata check failed: {e}")
    return flags

# ---------- STEP 5: Logo verification ----------
def verify_logo(image, logo_path=CBSE_LOGO_PATH, threshold=0.8):
    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"Logo file not found: {logo_path}")
    
    logo = cv2.imread(logo_path, cv2.IMREAD_GRAYSCALE)
    img_gray = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)

    # Resize logo if larger than page
    if logo.shape[0] > img_gray.shape[0] or logo.shape[1] > img_gray.shape[1]:
        logo = cv2.resize(logo, (min(logo.shape[1], img_gray.shape[1]),
                                 min(logo.shape[0], img_gray.shape[0])))

    res = cv2.matchTemplate(img_gray, logo, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    return len(loc[0]) > 0

# ---------- STEP 6: Template comparison ----------
def compare_template(image, template_path=TEMPLATE_PATH, threshold=0.85):
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    img_gray = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)

    # Resize template to match image size
    template_resized = cv2.resize(template, (img_gray.shape[1], img_gray.shape[0]))

    score, _ = ssim(img_gray, template_resized, full=True)
    return score >= threshold, score

# ---------- STEP 7: Main classification ----------
def classify_document(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    images = []

    # PDFs
    if ext == ".pdf":
        text = extract_pdf_text(file_path)
        images = pdf_to_images(file_path)
        if not text:
            text = ""
            for img in images:
                text += ocr_image(img)
    # Images
    elif ext in [".png", ".jpg", ".jpeg"]:
        text = ocr_image(Image.open(file_path))
        images = [Image.open(file_path)]
    else:
        raise ValueError("Unsupported file type. Only PDF, PNG, JPG are allowed.")

    # Parse details
    details = parse_details(text)
    metadata_flags = check_metadata(file_path)

    # Image-based checks (first page/image)
    first_image = images[0] if images else None

    if first_image:
        try:
            logo_ok = verify_logo(first_image)
        except Exception as e:
            print(f"Logo check failed: {e}")
            logo_ok = False

        try:
            template_ok = compare_template(first_image)
        except Exception as e:
            print(f"Template comparison failed: {e}")
            template_ok = False
    else:
        logo_ok = False
        template_ok = False



    # Final classification
    classification = "Likely Authentic"
    if metadata_flags or not logo_ok or not template_ok:
        classification = "Suspicious"

    return {
        'details': details,
        'metadata_flags': metadata_flags,
        'logo_verified': bool(logo_ok),
        'template_verified': bool(template_ok),
        'classification': classification
    }

# ---------- Example ----------
if __name__ == "__main__":
    test_file = "sample_marksheet.pdf"
    result = classify_document(test_file)
    print(result)
