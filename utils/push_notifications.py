import logging
import firebase_admin
from firebase_admin import credentials, messaging
from database import users_collection

logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK
try:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

def send_push_notification(user_id: str, title: str, message: str, data: dict = None):
    """
    Send push notification to a user via Firebase Cloud Messaging (FCM)
    
    Args:
        user_id: User's mobile or email
        title: Notification title
        message: Notification message
        data: Additional data to send with notification
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    try:
        # Get user's FCM token from database
        user = users_collection.find_one({"$or": [{"mobile": user_id}, {"email": user_id}]})
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return False
        
        fcm_token = user.get("fcmToken")
        push_enabled = user.get("pushEnabled", True)
        
        if not fcm_token:
            logger.info(f"No FCM token for user: {user_id}")
            return False
        
        if not push_enabled:
            logger.info(f"Push notifications disabled for user: {user_id}")
            return False
        
        # Create FCM message
        fcm_message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=message,
            ),
            data=data or {},
            token=fcm_token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    icon='notification_icon',
                    color='#4CAF50',
                    sound='default'
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )
        )
        
        # Send message
        response = messaging.send(fcm_message)
        logger.info(f"Push notification sent to {user_id}: {title} (Message ID: {response})")
        return True
            
    except messaging.UnregisteredError:
        logger.warning(f"Invalid FCM token for {user_id}, removing from database")
        users_collection.update_one(
            {"$or": [{"mobile": user_id}, {"email": user_id}]},
            {"$unset": {"fcmToken": ""}}
        )
        return False
    except Exception as e:
        logger.error(f"Error sending push notification to {user_id}: {e}")
        return False

def send_batch_push_notifications(notifications: list):
    """
    Send multiple push notifications in batch
    
    Args:
        notifications: List of dicts with keys: user_id, title, message, data
    
    Returns:
        dict: Success and failure counts
    """
    success_count = 0
    failure_count = 0
    
    for notification in notifications:
        user_id = notification.get("user_id")
        title = notification.get("title")
        message = notification.get("message")
        data = notification.get("data", {})
        
        if send_push_notification(user_id, title, message, data):
            success_count += 1
        else:
            failure_count += 1
    
    logger.info(f"Batch push notifications: {success_count} sent, {failure_count} failed")
    
    return {
        "success": success_count,
        "failed": failure_count
    }
