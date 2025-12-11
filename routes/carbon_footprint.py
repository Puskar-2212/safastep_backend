from fastapi import APIRouter, HTTPException
from database import carbon_footprints_collection, users_collection
from models import CarbonFootprintResult
from datetime import datetime
from bson import ObjectId

router = APIRouter()

@router.post("/carbon-footprint/save")
async def save_carbon_footprint(result: CarbonFootprintResult):
    """Save a carbon footprint quiz result"""
    try:
        # Verify user exists
        user = users_collection.find_one({"mobile": result.mobile})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prepare document
        timestamp = int(datetime.now().timestamp())
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        footprint_doc = {
            "mobile": result.mobile,
            "timestamp": timestamp,
            "date": date_str,
            "totalCO2": result.totalCO2,
            "yearlyTons": result.yearlyTons,
            "treesNeeded": result.treesNeeded,
            "impactLevel": result.impactLevel,
            "breakdown": result.breakdown,
            "vsGlobalAverage": result.vsGlobalAverage,
            "questionsAnswered": result.questionsAnswered,
            "quizVersion": "1.0",
            "completedAt": timestamp
        }
        
        # Insert into database
        result_insert = carbon_footprints_collection.insert_one(footprint_doc)
        
        # Update user's latest score (for quick access)
        users_collection.update_one(
            {"mobile": result.mobile},
            {
                "$set": {
                    "latestCO2Score": result.totalCO2,
                    "lastQuizDate": date_str,
                    "impactLevel": result.impactLevel
                }
            }
        )
        
        return {
            "success": True,
            "message": "Carbon footprint saved successfully",
            "id": str(result_insert.inserted_id),
            "timestamp": timestamp
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/carbon-footprint/latest/{mobile}")
async def get_latest_footprint(mobile: str):
    """Get user's latest carbon footprint result"""
    try:
        # Find latest result
        result = carbon_footprints_collection.find_one(
            {"mobile": mobile},
            sort=[("timestamp", -1)]
        )
        
        if not result:
            return {
                "success": True,
                "hasResult": False,
                "message": "No quiz results found"
            }
        
        # Convert ObjectId to string
        result["_id"] = str(result["_id"])
        
        return {
            "success": True,
            "hasResult": True,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/carbon-footprint/history/{mobile}")
async def get_footprint_history(mobile: str, limit: int = 10):
    """Get user's carbon footprint history"""
    try:
        # Find all results for user
        results = list(carbon_footprints_collection.find(
            {"mobile": mobile},
            sort=[("timestamp", -1)],
            limit=limit
        ))
        
        # Convert ObjectId to string
        for result in results:
            result["_id"] = str(result["_id"])
        
        return {
            "success": True,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/carbon-footprint/stats/{mobile}")
async def get_footprint_stats(mobile: str):
    """Get user's carbon footprint statistics and trends"""
    try:
        # Get all results
        results = list(carbon_footprints_collection.find(
            {"mobile": mobile},
            sort=[("timestamp", 1)]
        ))
        
        if not results:
            return {
                "success": True,
                "hasData": False,
                "message": "No quiz results found"
            }
        
        # Calculate statistics
        total_quizzes = len(results)
        latest = results[-1]
        first = results[0]
        
        # Calculate improvement
        if total_quizzes > 1:
            improvement = ((first["totalCO2"] - latest["totalCO2"]) / first["totalCO2"]) * 100
        else:
            improvement = 0
        
        # Get average by category
        category_totals = {}
        for result in results:
            for category, data in result.get("breakdown", {}).items():
                if category not in category_totals:
                    category_totals[category] = []
                category_totals[category].append(data.get("total", 0))
        
        category_averages = {
            category: sum(values) / len(values)
            for category, values in category_totals.items()
        }
        
        return {
            "success": True,
            "hasData": True,
            "stats": {
                "totalQuizzes": total_quizzes,
                "latestScore": latest["totalCO2"],
                "firstScore": first["totalCO2"],
                "improvement": round(improvement, 1),
                "averageScore": round(sum(r["totalCO2"] for r in results) / total_quizzes, 2),
                "bestScore": min(r["totalCO2"] for r in results),
                "categoryAverages": category_averages,
                "latestImpactLevel": latest["impactLevel"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/carbon-footprint/community-stats")
async def get_community_stats():
    """Get community-wide carbon footprint statistics"""
    try:
        # Get all latest results (one per user)
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$mobile",
                "latestResult": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$latestResult"}},
            {"$group": {
                "_id": None,
                "avgCO2": {"$avg": "$totalCO2"},
                "totalUsers": {"$sum": 1},
                "excellentCount": {
                    "$sum": {"$cond": [{"$eq": ["$impactLevel", "Excellent"]}, 1, 0]}
                },
                "goodCount": {
                    "$sum": {"$cond": [{"$eq": ["$impactLevel", "Good"]}, 1, 0]}
                },
                "averageCount": {
                    "$sum": {"$cond": [{"$eq": ["$impactLevel", "Average"]}, 1, 0]}
                },
                "highCount": {
                    "$sum": {"$cond": [{"$eq": ["$impactLevel", "High"]}, 1, 0]}
                }
            }}
        ]
        
        result = list(carbon_footprints_collection.aggregate(pipeline))
        
        if not result:
            return {
                "success": True,
                "hasData": False,
                "message": "No community data available"
            }
        
        stats = result[0]
        
        return {
            "success": True,
            "hasData": True,
            "communityStats": {
                "averageCO2": round(stats["avgCO2"], 2),
                "totalUsers": stats["totalUsers"],
                "impactLevels": {
                    "Excellent": stats["excellentCount"],
                    "Good": stats["goodCount"],
                    "Average": stats["averageCount"],
                    "High": stats["highCount"]
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
