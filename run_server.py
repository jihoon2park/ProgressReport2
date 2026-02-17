"""
IIS Deployment Entry Point
Listens on the port assigned by IIS via HTTP_PLATFORM_PORT environment variable.
"""
import os
import sys
import logging

# Setup file logging BEFORE importing app so we catch import errors
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'app_startup.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        # Get port: 1) command-line arg (IIS passes %HTTP_PLATFORM_PORT%)
        #           2) PORT env var
        #           3) default 5000
        if len(sys.argv) > 1:
            port = int(sys.argv[1])
        else:
            port = int(os.environ.get('PORT', 5000))
        
        logger.info(f"Starting Flask on 127.0.0.1:{port}")
        
        from app import app
        
        # httpPlatformHandler requires 127.0.0.1 (IIS proxies to localhost)
        app.run(
            host='127.0.0.1',
            port=port,
            debug=False
        )
    except Exception as e:
        logger.error(f"FATAL: Server failed to start: {e}", exc_info=True)
        sys.exit(1)
