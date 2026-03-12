from fastapi import APIRouter, HTTPException, Query
from bson import ObjectId
import time
import logging
from database import notifications_collection, users_collection

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/notifications/{identifier}")
async def get_notifications(
    identifier: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False)
):
    """
    Get notifications for a user (by mobile or email)
    """
    try:
        # Build query
        query = {"userId": identifier}
        if unread_only:
            query["read"] = False
        
        # Get notifications
        notifications = list(
            notifications_collection.find(query)
            .sort("createdAt", -1)
            .skip(skip)
            .limit(limit)
        )
        
        # Convert ObjectId to string
        for notification in notifications:
            notification["_id"] = str(notification["_id"])
        
        # Get unread count
        unread_count = notifications_collection.count_documents({
            "userId": identifier,
            "read": False
        })
        
        return {
            "success": True,
            "notifications": notifications,
            "unreadCount": unread_count,
            "total": len(notifications)
        }
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch notifications")

@router.put("/notifications/{notification_id}/read")
async def mark_notification_as_read(notification_id: str):
    """Mark a notification as read"""
    try:
        result = notifications_collection.update_one(
            {"_id": ObjectId(notification_id)},
            {"$set": {"read": True, "readAt": time.time()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {
            "success": True,
            "message": "Notification marked as read"
        }
        
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notification")

@router.put("/notifications/{identifier}/read-all")
async def mark_all_as_read(identifier: str):
    """Mark all notifications as read for a user"""
    try:
        result = notifications_collection.update_many(
            {"userId": identifier, "read": False},
            {"$set": {"read": True, "readAt": time.time()}}
        )
        
        return {
            "success": True,
            "message": f"Marked {result.modified_count} notifications as read"
        }
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        raise HTTPException(status_code=500, detail="Failed to update notifications")

@router.delete("/notifications/{notification_id}")
async def delete_notification(notification_id: str):
    """Delete a notification"""
    try:
        result = notifications_collection.delete_one({"_id": ObjectId(notification_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        return {
            "success": True,
            "message": "Notification deleted"
        }
        
    except Exception as e:
        logger.error(f"Error deleting notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete notification")

@router.delete("/notifications/{identifier}/clear-all")
async def clear_all_notifications(identifier: str):
    """Delete all notifications for a user"""
    try:
        result = notifications_collection.delete_many({"userId": identifier})
        
        return {
            "success": True,
            "message": f"Deleted {result.deleted_count} notifications"
        }
        
    except Exception as e:
        logger.error(f"Error clearing notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear notifications")

@router.get("/notifications/{identifier}/unread-count")
async def get_unread_count(identifier: str):
    """Get count of unread notifications"""
    try:
        count = notifications_collection.count_documents({
            "userId": identifier,
            "read": False
        })
        
        return {
            "success": True,
            "unreadCount": count
        }
        
    except Exception as e:
        logger.error(f"Error getting unread count: {e}")
        raise HTTPException(status_code=500, detail="Failed to get unread count")

# Helper function to create notifications (used by other routes)
def create_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    data: dict = None
):
    """
    Create an in-app notification for a user
    
    Types: post_approved, post_rejected, post_liked, milestone, comment
    """
    try:
        notification = {
            "userId": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "read": False,
            "createdAt": time.time()
        }
        
        result = notifications_collection.insert_one(notification)
        logger.info(f"Notification created for {user_id}: {title}")
        
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        return None
