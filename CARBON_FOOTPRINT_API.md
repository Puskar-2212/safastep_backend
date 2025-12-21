# Carbon Footprint API Documentation

## Overview
API endpoints for tracking and analyzing user carbon footprint data from CO₂ calculator quizzes.

## Endpoints

### 1. Save Carbon Footprint
**POST** `/carbon-footprint/save`

Save a user's carbon footprint quiz result.

**Request Body:**
```json
{
  "mobile": "+9779863204403",
  "totalCO2": 21.06,
  "yearlyTons": 7.69,
  "treesNeeded": 367,
  "impactLevel": "Average",
  "breakdown": {
    "Transportation": {
      "total": 5.2,
      "percentage": 42,
      "answers": []
    }
  },
  "vsGlobalAverage": {
    "percentage": -15,
    "betterThan": true
  },
  "questionsAnswered": 10
}
```

### 2. Get Latest Result
**GET** `/carbon-footprint/latest/{mobile}`

Retrieve user's most recent quiz result.

### 3. Get History
**GET** `/carbon-footprint/history/{mobile}?limit=10`

Get user's quiz history with optional limit.

### 4. Get Statistics
**GET** `/carbon-footprint/stats/{mobile}`

Get user statistics including improvement trends and averages.

### 5. Community Statistics
**GET** `/carbon-footprint/community-stats`

Get community-wide carbon footprint statistics.

## Impact Levels
- **Excellent**: < 10 kg CO₂/day
- **Good**: 10-20 kg CO₂/day
- **Average**: 20-30 kg CO₂/day
- **High**: > 30 kg CO₂/day

Global average: 12 kg CO₂/day
