"""
Advanced QR Code Processor with Multi-Library Support and Aggressive Preprocessing
Handles worst-case scenarios: blur, dim light, crushed plastic, shadows, etc.
"""
import cv2
import numpy as np
import base64
import io
from PIL import Image
import re
from difflib import SequenceMatcher
import logging

# Suppress verbose logging
logging.getLogger('PIL').setLevel(logging.WARNING)

class AdvancedQRProcessor:
    """Processes QR codes using multiple libraries and preprocessing techniques"""
    
    def __init__(self):
        # Initialize OpenCV QR detector
        self.cv_detector = cv2.QRCodeDetector()
        
        # Try to import optional libraries
        self.has_pyzbar = False
        try:
            from pyzbar import pyzbar
            self.pyzbar = pyzbar
            self.has_pyzbar = True
        except:
            pass
    
    def decode_base64_image(self, base64_string):
        """Convert base64 string to OpenCV image"""
        try:
            # Remove data URL prefix if present
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            
            # Decode base64
            img_data = base64.b64decode(base64_string)
            img = Image.open(io.BytesIO(img_data))
            
            # Convert to OpenCV format
            open_cv_image = np.array(img)
            if len(open_cv_image.shape) == 2:
                return open_cv_image
            else:
                return cv2.cvtColor(open_cv_image, cv2.COLOR_RGB2GRAY)
        except Exception as e:
            logging.error(f"Failed to decode image: {e}")
            return None
    
    def auto_brightness_contrast(self, image, clip_hist_percent=1):
        """Auto adjust brightness and contrast"""
        gray = image.copy()
        
        # Calculate grayscale histogram
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist_size = len(hist)
        
        # Calculate cumulative distribution
        accumulator = []
        accumulator.append(float(hist[0]))
        for index in range(1, hist_size):
            accumulator.append(accumulator[index - 1] + float(hist[index]))
        
        # Locate points to clip
        maximum = accumulator[-1]
        clip_hist_percent *= (maximum/100.0)
        clip_hist_percent = clip_hist_percent / 2.0
        
        # Locate left cut
        minimum_gray = 0
        while accumulator[minimum_gray] < clip_hist_percent:
            minimum_gray += 1
        
        # Locate right cut
        maximum_gray = hist_size - 1
        while accumulator[maximum_gray] >= (maximum - clip_hist_percent):
            maximum_gray -= 1
        
        # Calculate alpha and beta values
        alpha = 255 / (maximum_gray - minimum_gray)
        beta = -minimum_gray * alpha
        
        # Apply brightness/contrast adjustment
        auto_result = cv2.convertScaleAbs(gray, alpha=alpha, beta=beta)
        return auto_result
    
    def preprocess_image(self, image, method_index=0):
        """Apply different preprocessing methods based on index"""
        methods = []
        
        # Method 0: Original grayscale
        methods.append(image.copy())
        
        # Method 1: Auto brightness/contrast
        enhanced = self.auto_brightness_contrast(image)
        methods.append(enhanced)
        
        # Method 2: Histogram equalization
        equalized = cv2.equalizeHist(image)
        methods.append(equalized)
        
        # Method 3: CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl1 = clahe.apply(image)
        methods.append(cl1)
        
        # Method 4: Adaptive threshold
        adaptive = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                       cv2.THRESH_BINARY, 11, 2)
        methods.append(adaptive)
        
        # Method 5: Binary threshold with OTSU
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        methods.append(binary)
        
        # Method 6: Inverted binary
        _, inverted = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        methods.append(inverted)
        
        # Method 7: Median blur + threshold
        blurred = cv2.medianBlur(image, 5)
        _, blurred_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        methods.append(blurred_thresh)
        
        # Method 8: Gaussian blur + adaptive threshold
        gaussian = cv2.GaussianBlur(image, (5, 5), 0)
        gaussian_adaptive = cv2.adaptiveThreshold(gaussian, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                 cv2.THRESH_BINARY, 21, 10)
        methods.append(gaussian_adaptive)
        
        # Method 9: Morphological operations
        kernel = np.ones((3, 3), np.uint8)
        morph = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        methods.append(morph)
        
        # Method 10: Sharpening
        kernel_sharp = np.array([[-1,-1,-1],
                                 [-1, 9,-1],
                                 [-1,-1,-1]])
        sharpened = cv2.filter2D(image, -1, kernel_sharp)
        methods.append(sharpened)
        
        # Method 11: Extreme contrast boost
        min_val = np.min(image)
        max_val = np.max(image)
        if max_val > min_val:
            stretched = ((image - min_val) * (255 / (max_val - min_val))).astype(np.uint8)
        else:
            stretched = image
        methods.append(stretched)
        
        if method_index < len(methods):
            return methods[method_index]
        return image
    
    def add_border(self, image, border_size=30):
        """Add white border (quiet zone) around image"""
        return cv2.copyMakeBorder(image, border_size, border_size, border_size, border_size,
                                 cv2.BORDER_CONSTANT, value=255)
    
    def detect_and_correct_perspective(self, image):
        """Detect QR code corners and correct perspective"""
        try:
            # Find contours
            contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Find largest square-like contour
            for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:5]:
                peri = cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
                
                if len(approx) == 4:
                    # Found a quadrilateral
                    pts = approx.reshape(4, 2)
                    rect = np.zeros((4, 2), dtype="float32")
                    
                    # Order points
                    s = pts.sum(axis=1)
                    rect[0] = pts[np.argmin(s)]
                    rect[2] = pts[np.argmax(s)]
                    
                    diff = np.diff(pts, axis=1)
                    rect[1] = pts[np.argmin(diff)]
                    rect[3] = pts[np.argmax(diff)]
                    
                    # Compute width and height
                    (tl, tr, br, bl) = rect
                    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
                    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
                    maxWidth = max(int(widthA), int(widthB))
                    
                    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
                    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
                    maxHeight = max(int(heightA), int(heightB))
                    
                    # Destination points
                    dst = np.array([
                        [0, 0],
                        [maxWidth - 1, 0],
                        [maxWidth - 1, maxHeight - 1],
                        [0, maxHeight - 1]], dtype="float32")
                    
                    # Perspective transform
                    M = cv2.getPerspectiveTransform(rect, dst)
                    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
                    return warped
        except:
            pass
        
        return image
    
    def upscale_image(self, image, scale=2):
        """Upscale image for better resolution"""
        height, width = image.shape[:2]
        new_dim = (width * scale, height * scale)
        return cv2.resize(image, new_dim, interpolation=cv2.INTER_CUBIC)
    
    def decode_with_opencv(self, image):
        """Try decoding with OpenCV"""
        try:
            retval, decoded_info, points, straight_qrcode = self.cv_detector.detectAndDecodeMulti(image)
            if retval and decoded_info and decoded_info[0]:
                return decoded_info[0]
        except:
            pass
        return None
    
    def decode_with_pyzbar(self, image):
        """Try decoding with pyzbar"""
        if not self.has_pyzbar:
            return None
        
        try:
            decoded = self.pyzbar.decode(image)
            if decoded:
                return decoded[0].data.decode('utf-8')
        except:
            pass
        return None
    
    def fuzzy_match_correction(self, text, expected_patterns=None):
        """Apply fuzzy matching to correct common errors"""
        if not text:
            return text
        
        # Common OCR/scan errors
        corrections = {
            'httos://': 'https://',
            'httns://': 'https://',
            'httn://': 'http://',
            'httD://': 'http://',
            '0': 'O',  # Zero to O
            'l': '1',  # lowercase L to 1
            'I': '1',  # uppercase I to 1
        }
        
        corrected = text
        for wrong, right in corrections.items():
            corrected = corrected.replace(wrong, right)
        
        # If we have expected patterns, try to match
        if expected_patterns:
            best_match = corrected
            best_score = 0
            
            for pattern in expected_patterns:
                score = SequenceMatcher(None, corrected, pattern).ratio()
                if score > best_score and score > 0.7:  # 70% similarity threshold
                    best_score = score
                    best_match = pattern
            
            return best_match
        
        return corrected
    
    def process_image(self, base64_image, max_attempts=12):
        """Main processing function - tries everything"""
        image = self.decode_base64_image(base64_image)
        if image is None:
            return None, "Failed to decode image"
        
        results = []
        
        # Try all preprocessing methods
        for method_idx in range(max_attempts):
            # Preprocess
            processed = self.preprocess_image(image, method_idx)
            
            # Add border for quiet zone
            bordered = self.add_border(processed)
            
            # Try OpenCV
            result = self.decode_with_opencv(bordered)
            if result:
                results.append(('opencv', method_idx, result))
            
            # Try pyzbar
            result = self.decode_with_pyzbar(bordered)
            if result:
                results.append(('pyzbar', method_idx, result))
            
            # Try perspective correction
            corrected = self.detect_and_correct_perspective(processed)
            if corrected is not None:
                result = self.decode_with_opencv(corrected)
                if result:
                    results.append(('opencv_perspective', method_idx, result))
                
                result = self.decode_with_pyzbar(corrected)
                if result:
                    results.append(('pyzbar_perspective', method_idx, result))
            
            # Try upscaling
            upscaled = self.upscale_image(processed)
            result = self.decode_with_opencv(upscaled)
            if result:
                results.append(('opencv_upscaled', method_idx, result))
        
        # Return best result
        if results:
            # Most common result (voting)
            from collections import Counter
            qr_codes = [r[2] for r in results]
            most_common = Counter(qr_codes).most_common(1)[0][0]
            
            # Apply fuzzy correction
            corrected = self.fuzzy_match_correction(most_common)
            
            return corrected, f"Decoded using {results[0][0]} method {results[0][1]}"
        
        return None, "No QR code detected after all attempts"

# Global processor instance
qr_processor = AdvancedQRProcessor()