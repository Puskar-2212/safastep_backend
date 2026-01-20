import face_recognition
import numpy as np
import logging
from PIL import Image

logger = logging.getLogger(__name__)

class FaceVerifier:
    """Face detection and verification for user authentication"""
    
    def __init__(self):
        self.face_match_threshold = 0.6  # 60% confidence for match
        
    def detect_faces(self, image_path: str) -> dict:
        """
        Detect faces in an image
        Returns: dict with face count and face encodings
        """
        try:
            # Load image
            image = face_recognition.load_image_file(image_path)
            
            # Find all face locations
            face_locations = face_recognition.face_locations(image)
            
            # Get face encodings
            face_encodings = face_recognition.face_encodings(image, face_locations)
            
            return {
                "success": True,
                "face_count": len(face_locations),
                "face_locations": face_locations,
                "face_encodings": face_encodings,
                "has_face": len(face_locations) > 0
            }
            
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return {
                "success": False,
                "face_count": 0,
                "face_locations": [],
                "face_encodings": [],
                "has_face": False,
                "error": str(e)
            }
    
    def extract_face_encoding(self, image_path: str) -> dict:
        """
        Extract face encoding from profile picture
        Returns: dict with face encoding (128-dimensional array)
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
                    "error": "No face detected in image"
                }
            
            if detection_result["face_count"] > 1:
                return {
                    "success": False,
                    "error": f"Multiple faces detected ({detection_result['face_count']}). Please use a photo with only your face."
                }
            
            # Get the first (and only) face encoding
            face_encoding = detection_result["face_encodings"][0]
            
            # Convert to list for JSON serialization
            encoding_list = face_encoding.tolist()
            
            return {
                "success": True,
                "face_encoding": encoding_list,
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
        Compare profile face with face in post image
        Returns: dict with match result and confidence
        """
        try:
            # Convert profile encoding back to numpy array
            known_encoding = np.array(profile_encoding)
            
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
            post_encodings = detection_result["face_encodings"]
            
            # Calculate face distances (lower = more similar)
            face_distances = face_recognition.face_distance([known_encoding], post_encodings[0])
            
            # Convert distance to confidence (0-100%)
            confidence = (1 - face_distances[0]) * 100
            
            # Check if faces match
            matches = face_recognition.compare_faces(
                [known_encoding], 
                post_encodings[0],
                tolerance=self.face_match_threshold
            )
            
            matched = matches[0]
            
            # Additional check: if multiple faces, check all
            best_match = matched
            best_confidence = confidence
            
            if len(post_encodings) > 1:
                for encoding in post_encodings[1:]:
                    distances = face_recognition.face_distance([known_encoding], encoding)
                    current_confidence = (1 - distances[0]) * 100
                    
                    if current_confidence > best_confidence:
                        best_confidence = current_confidence
                        best_match = face_recognition.compare_faces(
                            [known_encoding], 
                            encoding,
                            tolerance=self.face_match_threshold
                        )[0]
            
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
