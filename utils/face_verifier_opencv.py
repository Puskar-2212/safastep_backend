import cv2
import numpy as np
import logging
from PIL import Image

logger = logging.getLogger(__name__)

class FaceVerifier:
    """Face detection and verification using OpenCV (no dlib required)"""
    
    def __init__(self):
        # Load OpenCV's pre-trained face detection model
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.face_match_threshold = 0.7  # 70% similarity for match
        
    def detect_faces(self, image_path: str) -> dict:
        """
        Detect faces in an image using OpenCV
        Returns: dict with face count and face regions
        """
        try:
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                return {
                    "success": False,
                    "face_count": 0,
                    "face_locations": [],
                    "has_face": False,
                    "error": "Failed to load image"
                }
            
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            face_locations = []
            face_features = []
            
            for (x, y, w, h) in faces:
                face_locations.append((x, y, w, h))
                # Extract face region
                face_roi = gray[y:y+h, x:x+w]
                # Resize to standard size for comparison
                face_roi_resized = cv2.resize(face_roi, (100, 100))
                face_features.append(face_roi_resized.flatten())
            
            return {
                "success": True,
                "face_count": len(faces),
                "face_locations": face_locations,
                "face_features": face_features,
                "has_face": len(faces) > 0
            }
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return {
                "success": False,
                "face_count": 0,
                "face_locations": [],
                "face_features": [],
                "has_face": False,
                "error": str(e)
            }
    
    def extract_face_encoding(self, image_path: str) -> dict:
        """
        Extract face features from profile picture
        Returns: dict with face features (simplified encoding)
        """
        try:
            detection_result = self.detect_faces(image_path)
            
            if not detection_result["success"]:
                return {
                    "success": False,
                    "error": detection_result.get("error", "Face detection failed")
                }
            
            if detection_result["face_count"] == 0:
                return {
                    "success": False,
                    "error": "No face detected in image. Please use a clear photo of your face."
                }
            
            if detection_result["face_count"] > 1:
                return {
                    "success": False,
                    "error": f"Multiple faces detected ({detection_result['face_count']}). Please use a photo with only your face."
                }
            
            # Get the first (and only) face features
            face_features = detection_result["face_features"][0]
            
            # Convert to list for JSON serialization
            features_list = face_features.tolist()
            
            return {
                "success": True,
                "face_encoding": features_list,
                "face_location": detection_result["face_locations"][0]
            }
            
        except Exception as e:
            logger.error(f"Error extracting face encoding: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def compare_faces(self, profile_encoding: list, post_image_path: str) -> dict:
        """
        Compare profile face with face in post image using correlation
        Returns: dict with match result and confidence
        """
        try:
            # Convert profile encoding back to numpy array
            known_features = np.array(profile_encoding)
            
            # Detect faces in post image
            detection_result = self.detect_faces(post_image_path)
            
            if not detection_result["success"]:
                return {
                    "success": False,
                    "matched": False,
                    "confidence": 0,
                    "error": detection_result.get("error", "Face detection failed")
                }
            
            if detection_result["face_count"] == 0:
                return {
                    "success": True,
                    "matched": False,
                    "confidence": 0,
                    "reason": "No face detected in post image"
                }
            
            # Compare with all detected faces
            post_features_list = detection_result["face_features"]
            
            best_match = False
            best_confidence = 0
            
            for post_features in post_features_list:
                # Calculate correlation coefficient (similarity)
                correlation = np.corrcoef(known_features, post_features)[0, 1]
                
                # Convert to percentage (0-100)
                confidence = max(0, min(100, correlation * 100))
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = confidence >= (self.face_match_threshold * 100)
            
            return {
                "success": True,
                "matched": best_match,
                "confidence": round(float(best_confidence), 2),
                "face_count": detection_result["face_count"],
                "reason": "Face verified" if best_match else "Face doesn't match profile"
            }
            
        except Exception as e:
            logger.error(f"Error comparing faces: {e}")
            return {
                "success": False,
                "matched": False,
                "confidence": 0,
                "error": str(e)
            }
    
    def verify_post_image(self, profile_encoding: list, post_image_path: str) -> dict:
        """
        Complete verification for post image
        Checks: face detection + face matching
        Returns: verification result with score
        """
        try:
            # Step 1: Detect faces in post
            detection_result = self.detect_faces(post_image_path)
            
            if not detection_result["success"]:
                return {
                    "verified": False,
                    "face_detected": False,
                    "face_matched": False,
                    "score": 0,
                    "confidence": 0,
                    "reason": detection_result.get("error", "Face detection failed")
                }
            
            if detection_result["face_count"] == 0:
                return {
                    "verified": False,
                    "face_detected": False,
                    "face_matched": False,
                    "score": 0,
                    "confidence": 0,
                    "reason": "No face detected. Please include your face in the photo."
                }
            
            # Step 2: Compare faces
            comparison_result = self.compare_faces(profile_encoding, post_image_path)
            
            if not comparison_result["success"]:
                return {
                    "verified": False,
                    "face_detected": True,
                    "face_matched": False,
                    "score": 20,  # Points for face detection only
                    "confidence": 0,
                    "reason": comparison_result.get("error", "Face comparison failed")
                }
            
            # Calculate score
            face_detection_score = 20  # 20 points for detecting face
            face_match_score = 30 if comparison_result["matched"] else 0  # 30 points for matching
            total_score = face_detection_score + face_match_score
            
            return {
                "verified": comparison_result["matched"],
                "face_detected": True,
                "face_matched": comparison_result["matched"],
                "score": total_score,
                "confidence": comparison_result["confidence"],
                "face_count": comparison_result["face_count"],
                "reason": comparison_result["reason"]
            }
            
        except Exception as e:
            logger.error(f"Error verifying post image: {e}")
            return {
                "verified": False,
                "face_detected": False,
                "face_matched": False,
                "score": 0,
                "confidence": 0,
                "reason": f"Verification error: {str(e)}"
            }
