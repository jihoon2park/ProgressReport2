"""
IIS Deployment Entry Point
Listens on the port assigned by IIS via HTTP_PLATFORM_PORT environment variable.
"""
import os
import sys
from app import app

if __name__ == '__main__':
    # Get port: 1) command-line arg (IIS passes %HTTP_PLATFORM_PORT%)
    #           2) PORT env var
    #           3) default 5000
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = int(os.environ.get('PORT', 5000))
    
    app.run(
        host='127.0.0.1',
        port=port,
        debug=False
    )
