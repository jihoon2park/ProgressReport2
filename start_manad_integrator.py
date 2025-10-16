#!/usr/bin/env python3
"""
MANAD Plus Integrator 시작 스크립트
CIMS 시스템에서 MANAD Plus와의 연동을 시작합니다.
"""

import sys
import logging
from manad_plus_integrator import MANADPlusIntegrator

# 로깅 설정
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
    """MANAD Plus Integrator 시작"""
    try:
        logger.info("MANAD Plus Integrator 시작 중...")
        
        # Integrator 인스턴스 생성
        integrator = MANADPlusIntegrator()
        
        # 폴링 시작
        success = integrator.start_polling()
        
        if success:
            logger.info("MANAD Plus Integrator가 성공적으로 시작되었습니다.")
            logger.info("5분마다 MANAD Plus에서 인시던트를 폴링합니다.")
            logger.info("종료하려면 Ctrl+C를 누르세요.")
            
            # 메인 스레드에서 대기
            try:
                while integrator.is_running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("사용자에 의해 중단됨")
                integrator.stop_polling()
                logger.info("MANAD Plus Integrator가 중지되었습니다.")
        else:
            logger.error("MANAD Plus Integrator 시작 실패")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"MANAD Plus Integrator 오류: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
