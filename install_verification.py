"""
Installation script for AI verification dependencies
Run this after updating requirements.txt
"""
import subprocess
import sys

def install_dependencies():
    """Install required packages for image verification"""
    packages = [
        "opencv-python",
        "imagehash", 
        "ultralytics",
        "numpy"
    ]
    
    print("Installing AI verification dependencies...")
    print("=" * 50)
    
    for package in packages:
        print(f"\nInstalling {package}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {package}: {e}")
            return False
    
    print("\n" + "=" * 50)
    print("✓ All dependencies installed successfully!")
    print("\nYOLO model (yolov8n.pt) will auto-download on first use (~6MB)")
    print("\nRestart your FastAPI server to apply changes.")
    return True

if __name__ == "__main__":
    success = install_dependencies()
    sys.exit(0 if success else 1)
