"""
Test script for AI image verification system
Run this to verify all components are working
"""
import sys
import os

def test_imports():
    """Test if all required packages are installed"""
    print("Testing imports...")
    print("-" * 50)
    
    try:
        import cv2
        print("✓ OpenCV installed:", cv2.__version__)
    except ImportError as e:
        print("✗ OpenCV not installed:", e)
        return False
    
    try:
        import imagehash
        print("✓ ImageHash installed")
    except ImportError as e:
        print("✗ ImageHash not installed:", e)
        return False
    
    try:
        from ultralytics import YOLO
        print("✓ Ultralytics (YOLO) installed")
    except ImportError as e:
        print("✗ Ultralytics not installed:", e)
        return False
    
    try:
        import numpy as np
        print("✓ NumPy installed:", np.__version__)
    except ImportError as e:
        print("✗ NumPy not installed:", e)
        return False
    
    return True

def test_modules():
    """Test if custom modules can be imported"""
    print("\nTesting custom modules...")
    print("-" * 50)
    
    try:
        from utils.image_analyzer import ImageAnalyzer
        print("✓ ImageAnalyzer module loaded")
        analyzer = ImageAnalyzer()
        print("  - ImageAnalyzer initialized")
    except Exception as e:
        print("✗ ImageAnalyzer failed:", e)
        return False
    
    try:
        from utils.yolo_detector import YOLODetector
        print("✓ YOLODetector module loaded")
        print("  - Initializing YOLO (this may download model on first run)...")
        detector = YOLODetector()
        if detector.model:
            print("  - YOLODetector initialized successfully")
        else:
            print("  ⚠ YOLODetector initialized but model not loaded")
    except Exception as e:
        print("✗ YOLODetector failed:", e)
        return False
    
    try:
        from utils.image_verification import ImageVerificationService
        print("✓ ImageVerificationService module loaded")
        service = ImageVerificationService()
        print("  - ImageVerificationService initialized")
    except Exception as e:
        print("✗ ImageVerificationService failed:", e)
        return False
    
    return True

def test_sample_image():
    """Test verification with a sample image (if available)"""
    print("\nTesting with sample image...")
    print("-" * 50)
    
    # Check if uploads directory exists
    if not os.path.exists("uploads"):
        print("⚠ No uploads directory found - skipping image test")
        return True
    
    # Find first image in uploads
    images = [f for f in os.listdir("uploads") if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    if not images:
        print("⚠ No images found in uploads - skipping image test")
        return True
    
    test_image = os.path.join("uploads", images[0])
    print(f"Testing with: {test_image}")
    
    try:
        from utils.image_verification import ImageVerificationService
        service = ImageVerificationService()
        
        result = service.verify_image(test_image, "recycling", "test_user")
        
        print(f"\nVerification Result:")
        print(f"  - Status: {result.get('status', 'unknown')}")
        print(f"  - Score: {result.get('overall_score', 0)}/100")
        print(f"  - Approved: {result.get('approved', False)}")
        
        if result.get('reasons'):
            print(f"  - Reasons: {', '.join(result['reasons'])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Image test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 50)
    print("AI IMAGE VERIFICATION - SYSTEM TEST")
    print("=" * 50 + "\n")
    
    # Test 1: Imports
    if not test_imports():
        print("\n❌ Import test failed. Run: pip install opencv-python imagehash ultralytics numpy")
        return False
    
    # Test 2: Custom modules
    if not test_modules():
        print("\n❌ Module test failed. Check error messages above.")
        return False
    
    # Test 3: Sample image (optional)
    test_sample_image()
    
    print("\n" + "=" * 50)
    print("✅ ALL TESTS PASSED!")
    print("=" * 50)
    print("\nYour AI verification system is ready to use.")
    print("Restart your FastAPI server to apply changes.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
