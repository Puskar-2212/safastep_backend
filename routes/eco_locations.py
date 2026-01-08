from fastapi import APIRouter, HTTPException, Query
from database import eco_locations_collection
from models import EcoLocationCreate, EcoLocationUpdate
from datetime import datetime
from bson import ObjectId
from typing import Optional

router = APIRouter()

@router.get("/eco-locations")
async def get_eco_locations(
    city: Optional[str] = Query(None, description="Filter by city (Kathmandu, Bhaktapur, Lalitpur)"),
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by status (for events)")
):
    """
    Get all eco-locations with optional filtering
    """
    try:
        # Build query filter
        query_filter = {}
        
        if city:
            query_filter["city"] = city
        
        if category:
            query_filter["category"] = category
        
        if status:
            query_filter["status"] = status
        
        # Fetch locations from database
        locations = list(eco_locations_collection.find(
            query_filter,
            {"_id": 0}  # Exclude MongoDB _id field
        ))
        
        # Auto-update event status for plantation events
        current_date = datetime.now().date()
        for location in locations:
            if location.get("category") == "plantation_event" and location.get("eventDate"):
                try:
                    event_date = datetime.fromisoformat(location["eventDate"].replace('Z', '+00:00')).date()
                    if event_date < current_date and location.get("status") != "completed":
                        # Update status in database
                        eco_locations_collection.update_one(
                            {"name": location["name"], "city": location["city"]},
                            {"$set": {"status": "completed"}}
                        )
                        location["status"] = "completed"
                except:
                    pass
        
        return {
            "success": True,
            "count": len(locations),
            "locations": locations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eco-locations/nearby")
async def get_nearby_locations(
    lat: float = Query(..., description="User's latitude"),
    lng: float = Query(..., description="User's longitude"),
    radius: int = Query(10, description="Search radius in kilometers"),
    category: Optional[str] = Query(None, description="Filter by category")
):
    """
    Get eco-locations near user's coordinates using geospatial query
    """
    try:
        # Build query filter
        query_filter = {
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [lng, lat]  # GeoJSON uses [longitude, latitude]
                    },
                    "$maxDistance": radius * 1000  # Convert km to meters
                }
            }
        }
        
        if category:
            query_filter["category"] = category
        
        # Fetch nearby locations
        locations = list(eco_locations_collection.find(
            query_filter,
            {"_id": 0}
        ))
        
        # Calculate distances for each location
        from math import radians, sin, cos, sqrt, atan2
        
        def calculate_distance(lat1, lon1, lat2, lon2):
            """Calculate distance using Haversine formula"""
            R = 6371  # Earth's radius in kilometers
            
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance = R * c
            
            return round(distance, 2)
        
        # Add distance to each location
        for location in locations:
            loc_lat = location.get("latitude")
            loc_lng = location.get("longitude")
            if loc_lat and loc_lng:
                distance = calculate_distance(lat, lng, loc_lat, loc_lng)
                location["distance"] = distance
        
        # Sort by distance
        locations.sort(key=lambda x: x.get("distance", float('inf')))
        
        return {
            "success": True,
            "count": len(locations),
            "locations": locations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/eco-locations/{location_id}")
async def get_location_by_id(location_id: str):
    """
    Get single eco-location by ID
    """
    try:
        # Try to find by ObjectId first
        try:
            location = eco_locations_collection.find_one(
                {"_id": ObjectId(location_id)},
                {"_id": 0}
            )
        except:
            # If not valid ObjectId, try finding by name or other identifier
            location = eco_locations_collection.find_one(
                {"name": location_id},
                {"_id": 0}
            )
        
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        
        return {
            "success": True,
            "location": location
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Admin Endpoints

@router.post("/admin/eco-locations/add")
async def add_eco_location(location: EcoLocationCreate):
    """
    Admin endpoint to add a new eco-location
    """
    try:
        # Prepare document for MongoDB
        timestamp = int(datetime.now().timestamp())
        
        location_doc = {
            "name": location.name,
            "category": location.category,
            "description": location.description,
            "city": location.city,
            "location": {
                "type": "Point",
                "coordinates": [location.longitude, location.latitude]  # GeoJSON format
            },
            "latitude": location.latitude,
            "longitude": location.longitude,
            "address": location.address,
            "contact": location.contact.dict() if location.contact else {},
            "hours": location.hours or {},
            "amenities": location.amenities or [],
            "images": location.images or [],
            "verified": True,
            "addedBy": "admin",
            "createdAt": timestamp,
            "updatedAt": timestamp
        }
        
        # Add event-specific fields if it's a plantation event
        if location.category == "plantation_event":
            location_doc.update({
                "eventDate": location.eventDate,
                "startTime": location.startTime,
                "endTime": location.endTime,
                "organizer": location.organizer,
                "targetTrees": location.targetTrees,
                "volunteersNeeded": location.volunteersNeeded,
                "volunteersRegistered": location.volunteersRegistered or 0,
                "estimatedCO2Offset": location.estimatedCO2Offset,
                "status": location.status or "upcoming"
            })
        
        # Insert into database
        result = eco_locations_collection.insert_one(location_doc)
        
        return {
            "success": True,
            "message": "Location added successfully",
            "id": str(result.inserted_id)
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/admin/eco-locations/{location_id}")
async def update_eco_location(location_id: str, location: EcoLocationUpdate):
    """
    Admin endpoint to update an existing eco-location
    """
    try:
        # Build update document (only include fields that are provided)
        update_doc = {}
        
        if location.name is not None:
            update_doc["name"] = location.name
        if location.category is not None:
            update_doc["category"] = location.category
        if location.description is not None:
            update_doc["description"] = location.description
        if location.city is not None:
            update_doc["city"] = location.city
        if location.latitude is not None and location.longitude is not None:
            update_doc["location"] = {
                "type": "Point",
                "coordinates": [location.longitude, location.latitude]
            }
            update_doc["latitude"] = location.latitude
            update_doc["longitude"] = location.longitude
        if location.address is not None:
            update_doc["address"] = location.address
        if location.contact is not None:
            update_doc["contact"] = location.contact.dict()
        if location.hours is not None:
            update_doc["hours"] = location.hours
        if location.amenities is not None:
            update_doc["amenities"] = location.amenities
        if location.images is not None:
            update_doc["images"] = location.images
        
        # Event-specific fields
        if location.eventDate is not None:
            update_doc["eventDate"] = location.eventDate
        if location.startTime is not None:
            update_doc["startTime"] = location.startTime
        if location.endTime is not None:
            update_doc["endTime"] = location.endTime
        if location.organizer is not None:
            update_doc["organizer"] = location.organizer
        if location.targetTrees is not None:
            update_doc["targetTrees"] = location.targetTrees
        if location.volunteersNeeded is not None:
            update_doc["volunteersNeeded"] = location.volunteersNeeded
        if location.volunteersRegistered is not None:
            update_doc["volunteersRegistered"] = location.volunteersRegistered
        if location.estimatedCO2Offset is not None:
            update_doc["estimatedCO2Offset"] = location.estimatedCO2Offset
        if location.status is not None:
            update_doc["status"] = location.status
        
        # Add updated timestamp
        update_doc["updatedAt"] = int(datetime.now().timestamp())
        
        # Update in database
        try:
            result = eco_locations_collection.update_one(
                {"_id": ObjectId(location_id)},
                {"$set": update_doc}
            )
        except:
            # Try by name if ObjectId fails
            result = eco_locations_collection.update_one(
                {"name": location_id},
                {"$set": update_doc}
            )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")
        
        return {
            "success": True,
            "message": "Location updated successfully"
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/admin/eco-locations/{location_id}")
async def delete_eco_location(location_id: str):
    """
    Admin endpoint to delete an eco-location
    """
    try:
        # Try to delete by ObjectId first
        try:
            result = eco_locations_collection.delete_one({"_id": ObjectId(location_id)})
        except:
            # Try by name if ObjectId fails
            result = eco_locations_collection.delete_one({"name": location_id})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Location not found")
        
        return {
            "success": True,
            "message": "Location deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
