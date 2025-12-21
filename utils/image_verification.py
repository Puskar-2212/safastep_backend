from utils.image_analyzer import ImageAnalyzer
from utils.yolo_detector import YOLODetector
from utils.face_verifier_opencv import FaceVerifier
from database import posts_collection, users_collection
import logging

logger = logging.getLogger(__name__)

class ImageVerificationService:
    """Main service for comprehensive image verification"""
    
    def __init__(self):
        self.analyzer = ImageAnalyzer()
        self.detector = YOLODetector()
        self.face_verifier = FaceVerifier()
        
    def verify_image(self, image_path: str, category: str, user_mobile: str) -> dict:
        """
        Complete image verification pipeline
        Returns: verification result with overall score and details
        """
        try:
            verification_result = {
                "approved": False,
                "overall_score": 0,
                "quality_check": {},
                "duplicate_check": {},
                "face_verification": {},
                "category_verification": {},
                "image_hash": None,
                "reasons": []
            }
            
            # Get user's profile face encoding
            user = users_collection.find_one({"mobile": user_mobile})
            if not user:
                verification_result["reasons"].append("User not found")
                return verification_result
            
            profile_face_encoding = user.get("faceEncoding")
            if not profile_face_encoding:
                verification_result["reasons"].append("Profile face not set. Please update your profile picture.")
                return verification_result
            
            # Step 1: Image Quality Analysis
            logger.info(f"Analyzing image quality: {image_path}")
            quality_result = self.analyzer.analyze_image(image_path)
            verification_result["quality_check"] = quality_result
            
            if not quality_result["valid"]:
                verification_result["reasons"].extend(quality_result["issues"])
                return verification_result
            
            quality_score = quality_result["quality_score"] * 0.1  # 10% weight (max 10 points)
            verification_result["image_hash"] = quality_result["image_hash"]
            
            # Step 2: Duplicate Detection
            logger.info("Checking for duplicates")
            existing_hashes = list(posts_collection.find(
                {"imageHash": {"$exists": True}},
                {"imageHash": 1, "_id": 1}
            ))
            
            existing_hashes_list = [
                {"hash": post["imageHash"], "post_id": str(post["_id"])}
                for post in existing_hashes
            ]
            
            duplicate_result = self.analyzer.check_duplicate(
                quality_result["image_hash"],
                existing_hashes_list
            )
            verification_result["duplicate_check"] = duplicate_result
            
            if duplicate_result["is_duplicate"]:
                verification_result["reasons"].append(
                    f"Duplicate image detected ({duplicate_result['similarity']:.1f}% similar)"
                )
                return verification_result
            
            duplicate_score = 10  # 10 points for not being duplicate
            
            # Step 3: Face Verification (NEW!)
            logger.info("Verifying face in post")
            face_result = self.face_verifier.verify_post_image(profile_face_encoding, image_path)
            verification_result["face_verification"] = face_result
            
            if not face_result["face_detected"]:
                verification_result["reasons"].append(face_result["reason"])
                # Don't return yet, continue to show all issues
            
            if face_result["face_detected"] and not face_result["face_matched"]:
                verification_result["reasons"].append(
                    f"{face_result['reason']} (Confidence: {face_result['confidence']:.1f}%)"
                )
            
            face_score = face_result["score"]  # 0-50 points (20 for detection + 30 for match)
            
            # Step 4: Category Verification with YOLO
            logger.info(f"Verifying category: {category}")
            category_result = self.detector.verify_category(image_path, category)
            verification_result["category_verification"] = category_result
            
            if not category_result["verified"]:
                verification_result["reasons"].append(category_result["reason"])
            
            category_score = category_result["score"] * 0.3  # 30% weight (max 30 points)
            
            # Calculate Overall Score
            overall_score = quality_score + duplicate_score + face_score + category_score
            verification_result["overall_score"] = round(overall_score, 2)
            
            # Determine approval status
            # STRICT: Must have face match to approve
            if not face_result["face_matched"]:
                verification_result["approved"] = False
                verification_result["status"] = "rejected"
                if "Face doesn't match" not in str(verification_result["reasons"]):
                    verification_result["reasons"].append("Face verification required")
            elif overall_score >= 70:
                verification_result["approved"] = True
                verification_result["status"] = "approved"
                verification_result["reasons"].append("Image verified successfully")
            elif overall_score >= 50:
                verification_result["approved"] = False
                verification_result["status"] = "pending_review"
                verification_result["reasons"].append("Image flagged for manual review")
            else:
                verification_result["approved"] = False
                verification_result["status"] = "rejected"
                if not verification_result["reasons"]:
                    verification_result["reasons"].append("Image failed verification checks")
            
            logger.info(f"Verification complete. Score: {overall_score}, Status: {verification_result['status']}")
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Error in verification pipeline: {e}")
            return {
                "approved": False,
                "overall_score": 0,
                "status": "error",
                "reasons": [f"Verification error: {str(e)}"],
                "quality_check": {},
                "duplicate_check": {},
                "face_verification": {},
                "category_verification": {},
                "image_hash": None
            }
    
    def get_verification_summary(self, verification_result: dict) -> str:
        """Generate human-readable verification summary"""
        score = verification_result["overall_score"]
        status = verification_result.get("status", "unknown")
        
        if status == "approved":
            return f"✓ Verified (Score: {score}/100)"
        elif status == "pending_review":
            return f"⚠ Pending Review (Score: {score}/100)"
        elif status == "rejected":
            return f"✗ Rejected (Score: {score}/100)"
        else:
            return f"Error in verification"
