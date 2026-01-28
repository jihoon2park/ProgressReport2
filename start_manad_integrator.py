#!/usr/bin/env python3
"""
MANAD Plus Integrator startup script
Starts integration between CIMS system and MANAD Plus.
"""

import sys
import logging
from manad_plus_integrator import MANADPlusIntegrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('manad_integrator.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Start MANAD Plus Integrator"""
    try:
        logger.info("Starting MANAD Plus Integrator...")
        
        # Create Integrator instance
        integrator = MANADPlusIntegrator()
        
        # Start polling
        success = integrator.start_polling()
        
        if success:
            logger.info("MANAD Plus Integrator started successfully.")
            logger.info("Polling incidents from MANAD Plus every 5 minutes.")
            logger.info("Press Ctrl+C to stop.")
            
            # Wait in main thread
            try:
                while integrator.is_running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Interrupted by user")
                integrator.stop_polling()
                logger.info("MANAD Plus Integrator stopped.")
        else:
            logger.error("Failed to start MANAD Plus Integrator")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"MANAD Plus Integrator error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
