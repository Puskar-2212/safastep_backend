# SafaStep Backend API

A FastAPI-based backend for the SafaStep eco-friendly social platform.

## Features

- User authentication with OTP verification
- Profile management with photo upload
- Post creation and management
- Like and comment functionality
- Eco points tracking

## Tech Stack

- FastAPI
- MongoDB
- Twilio (OTP)
- Python 3.12+

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```
MONGODB_URI=your_mongodb_uri
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_phone_number
BASE_URL=your_base_url
```

3. Run the server:
```bash
uvicorn main:app --reload
```

## API Endpoints

### Authentication
- `POST /send-otp` - Send OTP to mobile number
- `POST /verify-otp` - Verify OTP and create user

### User Management
- `GET /user/{mobile}` - Get user profile
- `POST /upload-profile-picture` - Upload profile picture
- `DELETE /delete-profile-picture/{mobile}` - Delete profile picture
- `POST /update-steps` - Update user's step count

### Posts
- `POST /posts` - Create a new post
- `GET /posts` - Get all posts (with pagination)
- `GET /posts/user/{mobile}` - Get user's posts
- `GET /posts/category/{category_id}` - Get posts by category
- `POST /posts/{post_id}/like` - Like/unlike a post
- `DELETE /posts/{post_id}` - Delete a post

## Project Structure

```
Auth_backend/
├── main.py              # Main application entry point
├── config.py            # Configuration and environment variables
├── database.py          # MongoDB connection and collections
├── models.py            # Data models (if needed)
├── routes/
│   ├── auth.py         # Authentication routes
│   ├── user.py         # User management routes
│   └── posts.py        # Post management routes
├── uploads/            # Uploaded files directory
└── requirements.txt    # Python dependencies
```

## License

MIT
