from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
from config import UPLOAD_DIR
from routes.auth import router as auth_router
from routes.user import router as user_router
from routes.posts import router as posts_router
from routes.carbon_footprint import router as carbon_router
from routes.eco_locations import router as eco_locations_router
from routes.admin import router as admin_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="SafaStep API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Health check endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "service": "SafaStep API"}

# Include routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(user_router, tags=["User"])
app.include_router(posts_router, tags=["Posts"])
app.include_router(carbon_router, tags=["Carbon Footprint"])
app.include_router(eco_locations_router, tags=["Eco-Locations"])
app.include_router(admin_router, tags=["Admin"])

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
