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
            # Try to find user by mobile or email
            if '@' in user_mobile:
                user = users_collection.find_one({"email": user_mobile})
            else:
                user = users_collection.find_one({"mobile": user_mobile})
            
            if not user:
                verification_result["reasons"].append("User not found")
                verification_result["status"] = "rejected"
                return verification_result
            
            profile_face_encoding = user.get("faceEncoding")
            if not profile_face_encoding:
                # Skip face verification if no profile picture
                verification_result["face_verification"] = {
                    "verified": True,
                    "score": 0,
                    "reason": "Face verification skipped - no profile picture set"
                }
                logger.info("Face verification skipped - user has no profile picture")
            else:
                # Perform face verification if profile picture exists
                logger.info("Performing face verification")
                face_result = self.face_verifier.verify_post_image(profile_face_encoding, image_path)
                verification_result["face_verification"] = face_result
                
                if not face_result["verified"]:
                    verification_result["reasons"].append(face_result["reason"])
                    # Don't reject, just lower the score
                    logger.warning("Face verification failed but continuing with other checks")
            
            # Step 1: Image Quality Analysis
            logger.info(f"Analyzing image quality: {image_path}")
            quality_result = self.analyzer.analyze_image(image_path)
            verification_result["quality_check"] = quality_result
            
            if not quality_result["valid"]:
                verification_result["reasons"].extend(quality_result["issues"])
                verification_result["status"] = "rejected"
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
                    f"This image has already been posted. Please upload a new photo ({duplicate_result['similarity']:.1f}% similar to existing post)"
                )
                verification_result["status"] = "rejected"
                return verification_result
            
            duplicate_score = 10  # 10 points for not being duplicate
            
            # Step 3: Category Verification with YOLO - LENIENT CHECK
            logger.info(f"Verifying category: {category}")
            category_result = self.detector.verify_category(image_path, category)
            verification_result["category_verification"] = category_result
            
            # Log what was detected for debugging
            logger.info(f"Detected objects: {category_result.get('detected_objects', [])}")
            logger.info(f"Matched objects: {category_result.get('matched_objects', [])}")
            
            # VERY LENIENT CATEGORY VERIFICATION - Send most to admin review
            if not category_result["verified"]:
                # Check if we detected any objects at all
                detected_count = len(category_result.get('detected_objects', []))
                
                if detected_count > 0:
                    # Give partial credit for detecting objects, even if not perfect match
                    partial_score = min(detected_count * 10, 40)  # Up to 40 points for detecting objects
                    
                    verification_result["reasons"].append(
                        f"AI detected {detected_count} objects. Sending for admin review."
                    )
                    verification_result["status"] = "pending_review"
                    verification_result["overall_score"] = quality_score + duplicate_score + partial_score
                    
                    # Add detected objects to help admin
                    detected_list = ", ".join(category_result.get('detected_objects', [])[:5])
                    verification_result["reasons"].append(f"Detected: {detected_list}")
                    return verification_result
                else:
                    # No objects detected - still send to admin review instead of rejecting
                    logger.warning("No objects detected by YOLO - sending to admin review")
                    verification_result["reasons"].append(
                        "AI couldn't detect objects clearly. Manual admin review required."
                    )
                    verification_result["status"] = "pending_review"
                    verification_result["overall_score"] = quality_score + duplicate_score + 20  # Give base score
                    return verification_result
            
            # Category verification passed - calculate category score
            category_score = min(category_result["score"] * 0.5, 50)  # Max 50 points from category
            logger.info(f"Category verified with score: {category_result['score']} -> {category_score} points")
            
            # Calculate overall verification score from multiple factors
            total_score = quality_score + duplicate_score + category_score
            verification_factors = [
                f"Image quality: {quality_result['quality_score']}/100",
                f"Category match: {len(category_result.get('matched_objects', []))} objects detected",
                "No duplicates found"
            ]
            
            # Face verification (optional)
            if profile_face_encoding:
                face_result = self.face_verifier.verify_post_image(profile_face_encoding, image_path)
                verification_result["face_verification"] = face_result
                if face_result["verified"]:
                    total_score += 20  # Bonus for face match
                    verification_factors.append("Face verified")
                else:
                    verification_factors.append("Face verification failed")
            else:
                verification_result["face_verification"] = {
                    "verified": True,
                    "score": 0,
                    "reason": "Face verification skipped - no profile picture"
                }
                verification_factors.append("Face verification skipped")
            
            # Device consistency check
            # Add other verification factors here
            
            verification_result["overall_score"] = total_score
            verification_result["verification_factors"] = verification_factors
            
            # Determine final status based on score
            if total_score >= 70:
                verification_result["status"] = "pending_review"
                verification_result["reasons"].append(f"High confidence verification (Score: {total_score:.1f}/100). Ready for admin approval.")
            elif total_score >= 50:
                verification_result["status"] = "pending_review"
                verification_result["reasons"].append(f"Good verification score (Score: {total_score:.1f}/100). Awaiting admin review.")
            else:
                verification_result["status"] = "pending_review"
                verification_result["reasons"].append(f"Lower confidence score (Score: {total_score:.1f}/100). Manual review recommended.")
            
            logger.info(f"Verification complete. Score: {total_score:.1f}/100, Status: {verification_result['status']}")
            
            return verification_result
            
        except Exception as e:
            logger.error(f"Error in verification pipeline: {e}")
            # Return a more graceful error that allows admin review
            return {
                "approved": False,
                "overall_score": 20,  # Give some score for manual review
                "status": "pending_review",  # Send to admin instead of error
                "reasons": [f"AI verification encountered an issue. Manual review required. (Technical: {str(e)[:100]})"],
                "quality_check": {"valid": True, "quality_score": 50, "issues": []},
                "duplicate_check": {"is_duplicate": False},
                "face_verification": {"verified": False, "reason": "Verification error"},
                "category_verification": {"verified": False, "detected_objects": [], "matched_objects": []},
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
