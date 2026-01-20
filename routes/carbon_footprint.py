from fastapi import APIRouter, HTTPException
from database import carbon_footprints_collection, users_collection, user_db
from models import CarbonFootprintResult
from datetime import datetime
from bson import ObjectId

router = APIRouter()

# CO2 Questions collection
co2_questions_collection = user_db["co2_questions"]

@router.post("/carbon-footprint/save")
async def save_carbon_footprint(result: CarbonFootprintResult):
    """Save a carbon footprint quiz result"""
    try:
        # Verify user exists - check by mobile or email
        identifier = result.mobile  # This field contains either mobile or email
        if '@' in identifier:
            user = users_collection.find_one({"email": identifier})
        else:
            user = users_collection.find_one({"mobile": identifier})
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Prepare document
        timestamp = int(datetime.now().timestamp())
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        footprint_doc = {
            "identifier": identifier,  # Store the identifier (mobile or email)
            "mobile": result.mobile,  # Keep for backward compatibility
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
            "completedAt": timestamp,
            
        }
        
        # Insert into database
        result_insert = carbon_footprints_collection.insert_one(footprint_doc)
        
        # Update user's latest score (for quick access)
        if '@' in identifier:
            users_collection.update_one(
                {"email": identifier},
                {
                    "$set": {
                        "latestCO2Score": result.totalCO2,
                        "lastQuizDate": date_str,
                        "impactLevel": result.impactLevel
                        
                    }
                }
            )
        else:
            users_collection.update_one(
                {"mobile": identifier},
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


@router.get("/carbon-footprint/latest/{identifier}")
async def get_latest_footprint(identifier: str):
    """Get user's latest carbon footprint result (works with mobile or email)"""
    try:
        # Find latest result by identifier
        result = carbon_footprints_collection.find_one(
            {"$or": [{"mobile": identifier}, {"identifier": identifier}]},
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


@router.get("/carbon-footprint/history/{identifier}")
async def get_footprint_history(identifier: str, limit: int = 10):
    """Get user's carbon footprint history (works with mobile or email)"""
    try:
        # Find all results for user
        results = list(carbon_footprints_collection.find(
            {"$or": [{"mobile": identifier}, {"identifier": identifier}]},
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


@router.get("/carbon-footprint/stats/{identifier}")
async def get_footprint_stats(identifier: str):
    """Get user's carbon footprint statistics and trends (works with mobile or email)"""
    try:
        # Get all results
        results = list(carbon_footprints_collection.find(
            {"$or": [{"mobile": identifier}, {"identifier": identifier}]},
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


@router.get("/co2-questions")
async def get_co2_questions():
    """Get all CO2 calculator questions from database"""
    try:
        # Fetch all active questions, sorted by order
        questions = list(co2_questions_collection.find(
            {"active": True},
            {"_id": 0}  # Exclude MongoDB _id field
        ).sort("order", 1))
        
        if not questions:
            return {
                "success": False,
                "message": "No questions found. Please run migration script.",
                "questions": []
            }
        
        return {
            "success": True,
            "count": len(questions),
            "questions": questions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/co2-questions/random")
async def get_random_questions(count: int = 10):
    """Get random selection of CO2 questions for quiz"""
    try:
        # Get questions by category
        transport_questions = list(co2_questions_collection.find(
            {"category": "Transportation", "active": True, "dependsOn": {"$exists": False}}
        ))
        energy_questions = list(co2_questions_collection.find(
            {"category": "Energy", "active": True, "dependsOn": {"$exists": False}}
        ))
        food_questions = list(co2_questions_collection.find(
            {"category": "Food", "active": True}
        ))
        waste_questions = list(co2_questions_collection.find(
            {"category": "Waste", "active": True}
        ))
        consumption_questions = list(co2_questions_collection.find(
            {"category": "Consumption", "active": True}
        ))
        water_questions = list(co2_questions_collection.find(
            {"category": "Water", "active": True}
        ))
        
        # Build selection (similar to frontend logic)
        import random
        selected = []
        
        # Add 1 transport + follow-up
        if transport_questions:
            transport = random.choice(transport_questions)
            selected.append(transport)
            if "followUp" in transport:
                followup = co2_questions_collection.find_one({"id": transport["followUp"]})
                if followup:
                    selected.append(followup)
        
        # Add 1 energy + follow-up
        if energy_questions:
            energy = random.choice(energy_questions)
            selected.append(energy)
            if "followUp" in energy:
                followup = co2_questions_collection.find_one({"id": energy["followUp"]})
                if followup:
                    selected.append(followup)
        
        # Add 2 food questions
        if food_questions:
            random.shuffle(food_questions)
            selected.extend(food_questions[:2])
        
        # Add 1-2 waste questions
        if waste_questions:
            random.shuffle(waste_questions)
            selected.extend(waste_questions[:random.choice([1, 2])])
        
        # Add 1-2 consumption questions
        if consumption_questions:
            random.shuffle(consumption_questions)
            selected.extend(consumption_questions[:random.choice([1, 2])])
        
        # Maybe add water (50% chance)
        if water_questions and random.random() > 0.5:
            selected.append(water_questions[0])
        
        # Limit to requested count
        selected = selected[:count]
        
        # Remove MongoDB _id field
        for q in selected:
            if "_id" in q:
                del q["_id"]
        
        return {
            "success": True,
            "count": len(selected),
            "questions": selected
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
