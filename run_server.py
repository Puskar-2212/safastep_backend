"""
Optimized server runner to prevent connection leaks and socket exhaustion
"""
import uvicorn
import sys

if __name__ == "__main__":
    # Run with optimized settings
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_delay=1,  # Delay before reloading
        workers=1,  # Single worker in development to prevent port exhaustion
        limit_concurrency=100,  # Limit concurrent connections
        limit_max_requests=1000,  # Restart worker after 1000 requests to prevent memory leaks
        timeout_keep_alive=5,  # Close keep-alive connections after 5 seconds
        timeout_graceful_shutdown=10,  # Give 10 seconds for graceful shutdown
        log_level="info",
    )
