from ultralytics import YOLO
import logging
import os

logger = logging.getLogger(__name__)

class YOLODetector:
    """YOLO-based object detection for eco-action verification"""
    
    # Category-specific objects mapping
    CATEGORY_OBJECTS = {
        "recycling": [
            "bottle", "plastic", "can", "paper", "cardboard", 
            "container", "cup", "bag", "box"
        ],
        "plantation": [  # Added plantation as alias
            "plant", "tree", "potted plant", "vase", "shovel",
            "soil", "garden", "leaf", "flower", "pot", "person",
            "glove", "hand", "tool"
        ],
        "tree_planting": [
            "plant", "tree", "potted plant", "vase", "shovel",
            "soil", "garden", "leaf"
        ],
        "energy": [  # Added energy as alias
            "solar panel", "wind turbine", "battery", "panel"
        ],
        "energy_conservation": [  # Added full name
            "solar panel", "wind turbine", "battery", "panel"
        ],
        "clean_energy": [
            "solar panel", "wind turbine", "battery", "panel"
        ],
        "transportation": [
            "bicycle", "bike", "bus", "train", "car", "vehicle",
            "motorcycle", "scooter"
        ],
        "waste_management": [
            "trash", "garbage", "bin", "bag", "broom", "cleaning",
            "bucket", "gloves"
        ],
        "waste-management": [  # Added hyphenated version
            "trash", "garbage", "bin", "bag", "broom", "cleaning",
            "bucket", "gloves"
        ],
        "water_conservation": [
            "water", "tank", "bucket", "tap", "faucet", "barrel",
            "container", "bottle"
        ]
    }
    
    def __init__(self, model_path: str = "yolov8n.pt"):
        """
        Initialize YOLO detector
        model_path: Path to YOLO model (yolov8n.pt is the nano/fastest version)
        """
        try:
            self.model = YOLO(model_path)
            logger.info(f"YOLO model loaded: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None
    
    def detect_objects(self, image_path: str, confidence: float = 0.15) -> dict:
        """
        Detect objects in image using YOLO
        Returns: dict with detected objects and their confidence scores
        """
        try:
            if self.model is None:
                return {
                    "success": False,
                    "error": "YOLO model not loaded",
                    "objects": []
                }
            
            # Run inference
            results = self.model(image_path, conf=confidence, verbose=False)
            
            detected_objects = []
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = result.names[cls_id]
                    
                    detected_objects.append({
                        "object": class_name,
                        "confidence": round(conf * 100, 2)
                    })
            
            return {
                "success": True,
                "objects": detected_objects,
                "count": len(detected_objects)
            }
            
        except Exception as e:
            logger.error(f"Error detecting objects: {e}")
            return {
                "success": False,
                "error": str(e),
                "objects": []
            }
    
    def verify_category(self, image_path: str, category: str) -> dict:
        """
        Verify if detected objects match the claimed category
        Returns: verification result with score and matched objects
        """
        try:
            # Detect objects
            detection_result = self.detect_objects(image_path)
            
            if not detection_result["success"]:
                return {
                    "verified": False,
                    "score": 0,
                    "reason": detection_result.get("error", "Detection failed"),
                    "detected_objects": [],
                    "matched_objects": []
                }
            
            detected_objects = detection_result["objects"]
            
            # No objects detected
            if len(detected_objects) == 0:
                return {
                    "verified": False,
                    "score": 0,
                    "reason": "No objects detected in image",
                    "detected_objects": [],
                    "matched_objects": []
                }
            
            # Get expected objects for category
            category_key = category.lower().replace(" ", "_")
            expected_objects = self.CATEGORY_OBJECTS.get(category_key, [])
            
            if not expected_objects:
                # Category not in our mapping, accept by default
                return {
                    "verified": True,
                    "score": 50,
                    "reason": "Category not in verification list",
                    "detected_objects": [obj["object"] for obj in detected_objects],
                    "matched_objects": []
                }
            
            # Check for matches
            matched_objects = []
            total_confidence = 0
            
            for detected in detected_objects:
                obj_name = detected["object"].lower()
                confidence = detected["confidence"]
                
                # Check if detected object matches any expected object
                for expected in expected_objects:
                    if expected in obj_name or obj_name in expected:
                        matched_objects.append({
                            "object": detected["object"],
                            "confidence": confidence
                        })
                        total_confidence += confidence
                        break
            
            # Calculate verification score
            if len(matched_objects) > 0:
                # Score based on: number of matches + average confidence
                match_score = min(len(matched_objects) * 15, 50)  # Max 50 points
                confidence_score = min(total_confidence / len(matched_objects), 50)  # Max 50 points
                final_score = match_score + confidence_score
                
                return {
                    "verified": True,
                    "score": round(final_score, 2),
                    "reason": f"Found {len(matched_objects)} relevant object(s)",
                    "detected_objects": [obj["object"] for obj in detected_objects],
                    "matched_objects": matched_objects
                }
            else:
                return {
                    "verified": False,
                    "score": 0,
                    "reason": f"No relevant objects found for category '{category}'",
                    "detected_objects": [obj["object"] for obj in detected_objects],
                    "matched_objects": []
                }
            
        except Exception as e:
            logger.error(f"Error verifying category: {e}")
            return {
                "verified": False,
                "score": 0,
                "reason": f"Verification error: {str(e)}",
                "detected_objects": [],
                "matched_objects": []
            }
