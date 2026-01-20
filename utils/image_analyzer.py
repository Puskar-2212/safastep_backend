import cv2
import numpy as np
from PIL import Image
import imagehash
import logging

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    """Analyzes image quality and generates perceptual hash for duplicate detection"""
    
    def __init__(self):
        self.min_width = 400
        self.min_height = 400
        self.blur_threshold = 100
        
    def analyze_image(self, image_path: str) -> dict:
        """
        Analyze image quality and generate hash
        Returns: dict with quality_score, issues, and image_hash
        """
        try:
            # Read image with OpenCV
            img = cv2.imread(image_path)
            if img is None:
                return {
                    "valid": False,
                    "quality_score": 0,
                    "issues": ["Failed to read image"],
                    "image_hash": None
                }
            
            issues = []
            quality_score = 100
            
            # Check 1: Resolution
            height, width = img.shape[:2]
            if width < self.min_width or height < self.min_height:
                issues.append(f"Low resolution: {width}x{height}")
                quality_score -= 30
            
            # Check 2: Blur detection (Laplacian variance)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            if laplacian_var < self.blur_threshold:
                issues.append(f"Image is blurry (score: {laplacian_var:.2f})")
                quality_score -= 25
            
            # Check 3: Brightness
            brightness = np.mean(gray)
            if brightness < 30:
                issues.append("Image is too dark")
                quality_score -= 20
            elif brightness > 225:
                issues.append("Image is too bright")
                quality_score -= 20
            
            # Check 4: Screenshot detection (check for UI elements patterns)
            # Simple heuristic: screenshots often have solid color bars at top/bottom
            top_row = gray[0:10, :]
            bottom_row = gray[-10:, :]
            if np.std(top_row) < 5 or np.std(bottom_row) < 5:
                issues.append("Possible screenshot detected")
                quality_score -= 15
            
            # Generate perceptual hash for duplicate detection
            pil_image = Image.open(image_path)
            img_hash = str(imagehash.phash(pil_image))
            
            return {
                "valid": quality_score >= 20,
                "quality_score": max(0, quality_score),
                "issues": issues,
                "image_hash": img_hash,
                "dimensions": {"width": width, "height": height},
                "brightness": float(brightness),
                "blur_score": float(laplacian_var)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {
                "valid": False,
                "quality_score": 0,
                "issues": [f"Analysis error: {str(e)}"],
                "image_hash": None
            }
    
    def check_duplicate(self, image_hash: str, existing_hashes: list, threshold: int = 5) -> dict:
        """
        Check if image is duplicate by comparing hashes
        threshold: Hamming distance (lower = more similar, 0 = identical)
        """
        try:
            current_hash = imagehash.hex_to_hash(image_hash)
            
            for existing in existing_hashes:
                existing_hash = imagehash.hex_to_hash(existing["hash"])
                distance = current_hash - existing_hash
                
                if distance <= threshold:
                    similarity = (1 - distance / 64) * 100  # Convert to percentage
                    return {
                        "is_duplicate": True,
                        "similarity": similarity,
                        "matched_post_id": existing.get("post_id"),
                        "distance": distance
                    }
            
            return {
                "is_duplicate": False,
                "similarity": 0,
                "matched_post_id": None,
                "distance": None
            }
            
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return {
                "is_duplicate": False,
                "similarity": 0,
                "matched_post_id": None,
                "distance": None
            }
