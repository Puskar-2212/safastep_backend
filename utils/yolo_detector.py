from ultralytics import YOLO
import logging
import os
import cv2
import numpy as np
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)

class YOLODetector:
    """Enhanced YOLO-based object detection for eco-action verification"""
    
    # Expanded category-specific objects mapping with more variations
    CATEGORY_OBJECTS = {
        "recycling": [
            "bottle", "plastic bottle", "water bottle", "can", "paper", "cardboard", 
            "container", "cup", "bag", "box", "trash", "garbage", "bin",
            "recycling bin", "waste", "packaging", "carton", "glass"
        ],
        "plantation": [
            "plant", "tree", "potted plant", "vase", "shovel", "spade",
            "soil", "garden", "leaf", "flower", "pot", "person", "woman", "man",
            "glove", "hand", "tool", "gardening", "seedling", "sapling",
            "dirt", "earth", "watering can", "trowel", "bucket"
        ],
        "tree_planting": [
            "plant", "tree", "potted plant", "vase", "shovel", "spade",
            "soil", "garden", "leaf", "person", "woman", "man", "seedling",
            "sapling", "dirt", "earth", "pot", "container", "tool"
        ],
        "energy": [
            "solar panel", "wind turbine", "battery", "panel", "solar",
            "turbine", "generator", "power", "electricity"
        ],
        "energy_conservation": [
            "solar panel", "wind turbine", "battery", "panel", "solar",
            "light", "lamp", "bulb", "switch", "electrical"
        ],
        "clean_energy": [
            "solar panel", "wind turbine", "battery", "panel", "solar",
            "turbine", "generator", "renewable"
        ],
        "transportation": [
            "bicycle", "bike", "bus", "train", "car", "vehicle",
            "motorcycle", "scooter", "person", "rider", "wheel",
            "motorbike", "moped", "cycle", "helmet"
        ],
        "waste_management": [
            "trash", "garbage", "bin", "bag", "broom", "cleaning",
            "bucket", "gloves", "person", "cleaner", "sweep", "waste"
        ],
        "waste-management": [
            "trash", "garbage", "bin", "bag", "broom", "cleaning",
            "bucket", "gloves", "person", "cleaner", "sweep", "waste"
        ],
        "water_conservation": [
            "water", "tank", "bucket", "tap", "faucet", "barrel",
            "container", "bottle", "person", "pipe", "hose"
        ]
    }
    
    def __init__(self, model_path: str = "yolov8s.pt"):
        """
        Initialize YOLO detector with better model
        model_path: Path to YOLO model (yolov8s.pt is more accurate than nano)
        """
        try:
            # Try to use a more accurate model
            if not os.path.exists(model_path):
                logger.info(f"Model {model_path} not found, downloading...")
            
            self.model = YOLO(model_path)
            logger.info(f"YOLO model loaded: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            # Fallback to nano model
            try:
                self.model = YOLO("yolov8n.pt")
                logger.info("Fallback to yolov8n.pt model")
            except:
                self.model = None
    
    def preprocess_image(self, image_path: str) -> str:
        """
        Enhance image quality before detection for better results
        """
        try:
            # Read image
            img = cv2.imread(image_path)
            if img is None:
                return image_path
            
            # Resize if too large (YOLO works better with certain sizes)
            height, width = img.shape[:2]
            if width > 1280 or height > 1280:
                scale = 1280 / max(width, height)
                new_width = int(width * scale)
                new_height = int(height * scale)
                img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            # Enhance contrast and brightness
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            
            # Merge channels and convert back
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            # Sharpen the image
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            enhanced = cv2.filter2D(enhanced, -1, kernel)
            
            # Save enhanced image
            enhanced_path = image_path.replace('.jpg', '_enhanced.jpg').replace('.png', '_enhanced.png')
            cv2.imwrite(enhanced_path, enhanced)
            
            return enhanced_path
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return image_path
    def detect_objects(self, image_path: str, confidence: float = 0.05) -> dict:
        """
        Detect objects in image using YOLO with enhanced preprocessing
        Returns: dict with detected objects and their confidence scores
        """
        try:
            if self.model is None:
                logger.error("YOLO model is None - not loaded properly")
                return {
                    "success": False,
                    "error": "YOLO model not loaded",
                    "objects": []
                }
            
            logger.info(f"Starting object detection on: {image_path}")
            
            # Try detection on original image first (preprocessing might make it worse)
            all_detections = []
            
            # Try different confidence thresholds - start with very low
            for conf_threshold in [0.01, 0.05, 0.1, 0.2, 0.25]:
                try:
                    logger.info(f"Trying detection with confidence threshold: {conf_threshold}")
                    results = self.model(image_path, conf=conf_threshold, verbose=False, imgsz=640)
                    
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None and len(boxes) > 0:
                            logger.info(f"Found {len(boxes)} boxes at confidence {conf_threshold}")
                            for box in boxes:
                                cls_id = int(box.cls[0])
                                conf = float(box.conf[0])
                                class_name = result.names[cls_id]
                                
                                logger.info(f"Detected: {class_name} with confidence {conf:.2f}")
                                
                                # Add detection if not already found with higher confidence
                                existing = next((d for d in all_detections if d["object"] == class_name), None)
                                if not existing or conf > existing["confidence"]:
                                    if existing:
                                        all_detections.remove(existing)
                                    
                                    all_detections.append({
                                        "object": class_name,
                                        "confidence": round(conf * 100, 2)
                                    })
                        else:
                            logger.info(f"No boxes found at confidence {conf_threshold}")
                except Exception as e:
                    logger.error(f"Detection failed at confidence {conf_threshold}: {e}")
                    continue
            
            # If no detections on original, try enhanced image
            if len(all_detections) == 0:
                logger.info("No detections on original image, trying enhanced version")
                enhanced_path = self.preprocess_image(image_path)
                
                try:
                    results = self.model(enhanced_path, conf=0.01, verbose=False, imgsz=640)
                    for result in results:
                        boxes = result.boxes
                        if boxes is not None:
                            for box in boxes:
                                cls_id = int(box.cls[0])
                                conf = float(box.conf[0])
                                class_name = result.names[cls_id]
                                
                                all_detections.append({
                                    "object": class_name,
                                    "confidence": round(conf * 100, 2)
                                })
                except Exception as e:
                    logger.error(f"Enhanced detection also failed: {e}")
                
                # Clean up enhanced image
                try:
                    if enhanced_path != image_path and os.path.exists(enhanced_path):
                        os.remove(enhanced_path)
                except:
                    pass
            
            # Sort by confidence
            all_detections.sort(key=lambda x: x["confidence"], reverse=True)
            
            logger.info(f"Total detections: {len(all_detections)}")
            if len(all_detections) > 0:
                logger.info(f"Top detections: {all_detections[:5]}")
            
            return {
                "success": True,
                "objects": all_detections,
                "count": len(all_detections)
            }
            
        except Exception as e:
            logger.error(f"Error detecting objects: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "objects": []
            }
    
    def verify_category(self, image_path: str, category: str) -> dict:
        """
        Enhanced category verification with fuzzy matching and better scoring
        Returns: verification result with score and matched objects
        """
        try:
            # Detect objects
            detection_result = self.detect_objects(image_path)
            
            if not detection_result["success"]:
                logger.error(f"Detection failed: {detection_result.get('error', 'Unknown error')}")
                # Don't fail completely - return partial result for admin review
                return {
                    "verified": False,
                    "score": 20,
                    "reason": f"Object detection encountered an issue. Manual review recommended.",
                    "detected_objects": [],
                    "matched_objects": []
                }
            
            detected_objects = detection_result["objects"]
            
            # Log all detected objects
            logger.info(f"Total objects detected: {len(detected_objects)}")
            if detected_objects:
                logger.info(f"Objects: {[obj['object'] for obj in detected_objects]}")
            
            # No objects detected
            if len(detected_objects) == 0:
                logger.warning("No objects detected in image")
                return {
                    "verified": False,
                    "score": 0,
                    "reason": f"No objects detected. Image may be unclear or not match {category} category.",
                    "detected_objects": [],
                    "matched_objects": []
                }
            
            # Get expected objects for category
            category_key = category.lower().replace(" ", "_").replace("-", "_")
            expected_objects = self.CATEGORY_OBJECTS.get(category_key, [])
            
            logger.info(f"Category: {category} -> Key: {category_key}")
            logger.info(f"Expected objects: {expected_objects[:5]}...")  # Log first 5
            
            if not expected_objects:
                # Category not in our mapping, be more lenient
                logger.info(f"Category '{category}' not in verification list, checking for general eco objects")
                # Check for any eco-related objects
                eco_objects = ["person", "plant", "bottle", "bag", "container", "tool", "bicycle", "motorcycle"]
                for detected in detected_objects:
                    if any(eco_obj in detected["object"].lower() for eco_obj in eco_objects):
                        logger.info(f"Found eco-related object: {detected['object']}")
                        return {
                            "verified": True,
                            "score": 60,
                            "reason": f"General eco-related objects detected: {detected['object']}",
                            "detected_objects": [obj["object"] for obj in detected_objects],
                            "matched_objects": [detected]
                        }
                
                return {
                    "verified": False,
                    "score": 30,
                    "reason": f"Category '{category}' not recognized, manual review recommended",
                    "detected_objects": [obj["object"] for obj in detected_objects],
                    "matched_objects": []
                }
            
            # Enhanced matching with fuzzy logic
            matched_objects = []
            total_confidence = 0
            
            for detected in detected_objects:
                obj_name = detected["object"].lower()
                confidence = detected["confidence"]
                
                # Direct match
                for expected in expected_objects:
                    expected_lower = expected.lower()
                    
                    # Exact match
                    if expected_lower == obj_name:
                        logger.info(f"Exact match: {obj_name} == {expected_lower}")
                        matched_objects.append({
                            "object": detected["object"],
                            "confidence": confidence,
                            "match_type": "exact"
                        })
                        total_confidence += confidence
                        break
                    
                    # Partial match (contains)
                    elif expected_lower in obj_name or obj_name in expected_lower:
                        logger.info(f"Partial match: {obj_name} ~ {expected_lower}")
                        matched_objects.append({
                            "object": detected["object"],
                            "confidence": confidence * 0.8,  # Slightly lower for partial match
                            "match_type": "partial"
                        })
                        total_confidence += confidence * 0.8
                        break
                    
                    # Fuzzy match for similar words
                    elif self._fuzzy_match(obj_name, expected_lower):
                        logger.info(f"Fuzzy match: {obj_name} ~~ {expected_lower}")
                        matched_objects.append({
                            "object": detected["object"],
                            "confidence": confidence * 0.6,  # Lower for fuzzy match
                            "match_type": "fuzzy"
                        })
                        total_confidence += confidence * 0.6
                        break
            
            logger.info(f"Matched objects: {len(matched_objects)}")
            
            # Calculate verification score with more lenient criteria
            if len(matched_objects) > 0:
                # Base score for having matches
                base_score = 40
                
                # Bonus for number of matches (up to 30 points)
                match_bonus = min(len(matched_objects) * 10, 30)
                
                # Confidence bonus (up to 30 points)
                avg_confidence = total_confidence / len(matched_objects)
                confidence_bonus = min(avg_confidence * 0.3, 30)
                
                final_score = base_score + match_bonus + confidence_bonus
                
                logger.info(f"Verification passed! Score: {final_score:.2f}")
                
                return {
                    "verified": True,
                    "score": round(final_score, 2),
                    "reason": f"Found {len(matched_objects)} relevant object(s) for {category}",
                    "detected_objects": [obj["object"] for obj in detected_objects],
                    "matched_objects": matched_objects
                }
            else:
                # Even if no direct matches, check for people (common in eco activities)
                people_detected = [obj for obj in detected_objects if "person" in obj["object"].lower() or "man" in obj["object"].lower() or "woman" in obj["object"].lower()]
                
                if people_detected and category.lower() in ["plantation", "tree_planting", "waste_management", "recycling", "transportation"]:
                    logger.info(f"Found person in {category} category - likely valid")
                    return {
                        "verified": True,
                        "score": 50,
                        "reason": f"Human activity detected for {category} - likely eco action",
                        "detected_objects": [obj["object"] for obj in detected_objects],
                        "matched_objects": people_detected
                    }
                
                # Build helpful error message
                detected_list = ", ".join([obj["object"] for obj in detected_objects[:5]])
                logger.warning(f"No matches found. Detected: {detected_list}")
                return {
                    "verified": False,
                    "score": 20,  # Give some score for detecting objects
                    "reason": f"Detected objects ({detected_list}) don't clearly match {category}. Manual review recommended.",
                    "detected_objects": [obj["object"] for obj in detected_objects],
                    "matched_objects": []
                }
            
        except Exception as e:
            logger.error(f"Error verifying category: {e}", exc_info=True)
            return {
                "verified": False,
                "score": 20,  # Give base score for manual review
                "reason": f"Verification error - manual review required",
                "detected_objects": [],
                "matched_objects": []
            }
    
    def _fuzzy_match(self, word1: str, word2: str) -> bool:
        """Simple fuzzy matching for similar words"""
        # Check if words share significant characters
        if len(word1) < 3 or len(word2) < 3:
            return False
        
        # Check for common substrings
        for i in range(len(word1) - 2):
            substring = word1[i:i+3]
            if substring in word2:
                return True
        
        return False
