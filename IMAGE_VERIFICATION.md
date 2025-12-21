# AI-Powered Image Verification System

## Overview
SafaStep uses a comprehensive AI verification system to ensure authentic eco-friendly actions and prevent fraud.

## Components

### 1. Image Quality Analysis (OpenCV)
- **Resolution Check**: Minimum 400x400 pixels
- **Blur Detection**: Using Laplacian variance
- **Brightness Analysis**: Detects too dark/bright images
- **Screenshot Detection**: Identifies possible screenshots
- **Weight**: 20% of overall score

### 2. Duplicate Detection (ImageHash)
- **Perceptual Hashing**: Generates unique fingerprint for each image
- **Similarity Threshold**: 95% similarity = duplicate
- **Prevents**: Users from reposting same image multiple times
- **Weight**: 30 points (fixed)

### 3. Category Verification (YOLOv8)
- **Object Detection**: Identifies objects in images
- **Category Matching**: Verifies objects match claimed eco-action
- **Confidence Scoring**: Based on detection confidence
- **Weight**: 50% of overall score

## Category-Object Mapping

| Category | Expected Objects |
|----------|-----------------|
| Recycling | bottle, plastic, can, paper, cardboard, container |
| Tree Planting | plant, tree, potted plant, shovel, soil, garden |
| Clean Energy | solar panel, wind turbine, battery, panel |
| Transportation | bicycle, bike, bus, train, car, vehicle |
| Waste Management | trash, garbage, bin, bag, broom, cleaning |
| Water Conservation | water, tank, bucket, tap, faucet, barrel |

## Scoring System

```
Total Score = Quality (20%) + Duplicate (30) + Category (50%)

Score Ranges:
- 70-100: ✓ Auto-Approved
- 50-69:  ⚠ Pending Manual Review
- 0-49:   ✗ Rejected
```

## Installation

```bash
# Install dependencies
pip install opencv-python imagehash ultralytics numpy

# YOLO model will auto-download on first use (yolov8n.pt ~6MB)
```

## API Response

### Success (Approved)
```json
{
  "success": true,
  "message": "Post created successfully",
  "post": {
    "_id": "...",
    "verificationScore": 85.5,
    "verificationStatus": "approved",
    "detectedObjects": [
      {"object": "bottle", "confidence": 92.3},
      {"object": "plastic", "confidence": 87.1}
    ]
  }
}
```

### Failure (Rejected)
```json
{
  "detail": {
    "message": "Image verification failed",
    "status": "rejected",
    "score": 35.2,
    "reasons": [
      "Image is blurry (score: 45.23)",
      "No relevant objects found for category 'Recycling'"
    ],
    "details": {
      "quality": {...},
      "duplicate": {...},
      "category": {...}
    }
  }
}
```

## Database Schema

New fields added to `posts` collection:

```javascript
{
  imageHash: "a1b2c3d4e5f6...",           // Perceptual hash
  verificationScore: 85.5,                 // Overall score (0-100)
  verificationStatus: "approved",          // approved/pending_review/rejected
  detectedObjects: [                       // Objects found by YOLO
    {object: "bottle", confidence: 92.3}
  ]
}
```

## Performance

- **Image Analysis**: ~100ms
- **Duplicate Check**: ~50ms
- **YOLO Detection**: ~200-500ms (CPU) / ~50-100ms (GPU)
- **Total**: ~350-650ms per image

## Future Enhancements

1. **GPU Acceleration**: Use CUDA for faster YOLO inference
2. **Custom Training**: Train YOLO on eco-specific dataset
3. **Caption Analysis**: Use NLP to verify caption relevance
4. **EXIF Metadata**: Check photo timestamp and location
5. **User Reputation**: Track user verification history

## Troubleshooting

### YOLO Model Download
First run will download yolov8n.pt (~6MB). Ensure internet connection.

### Memory Issues
Use `yolov8n.pt` (nano) for low-memory servers. For better accuracy, use `yolov8s.pt` (small).

### False Rejections
Adjust thresholds in `utils/image_verification.py`:
- Lower quality threshold (currently 20)
- Adjust category score weight (currently 50%)
- Add more objects to category mapping
