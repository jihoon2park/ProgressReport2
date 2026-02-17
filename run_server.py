"""
IIS Deployment Entry Point
Listens on the port assigned by IIS via HTTP_PLATFORM_PORT environment variable.
"""
import os
import sys
from app import app

if __name__ == '__main__':
    # Get the port IIS assigned to us via environment variable
    port = int(os.environ.get('PORT', 5000))
    
    # Run the Flask app on the IIS-assigned port
    # Note: For production, debug should be False
    app.run(
        host='127.0.0.1',
        port=port,
        debug=False
    )
