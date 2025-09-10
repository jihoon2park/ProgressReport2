"""
Incident (Adverse Event) 데이터를 가져오는 API 모듈
"""

import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from config import SITE_SERVERS, get_api_headers

logger = logging.getLogger(__name__)

class IncidentAPI:
    """Incident 데이터를 가져오는 API 클라이언트"""
    
    def __init__(self, site: str):
        self.site = site
        self.server_ip = SITE_SERVERS.get(site)
        if not self.server_ip:
            raise ValueError(f"Unknown site: {site}")
        
        self.base_url = f"http://{self.server_ip}"
        logger.info(f"Initialized Incident API for {site} at {self.base_url}")
    
    def fetch_incidents(self, start_date: str, end_date: str) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """지정된 기간의 incident 데이터를 가져옵니다."""
        try:
            # API 엔드포인트
            url = f"{self.base_url}/api/adverseevent"
            
            # 파라미터 설정
            params = {}
            
            # changedSinceDateTimeUTC 파라미터 (시작 날짜부터)
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                    params['changedsincedatetimeutc'] = start_dt.isoformat()
                except ValueError as e:
                    logger.warning(f"Invalid start_date format: {start_date}, error: {e}")
            
            # 사이트별 인증 헤더 가져오기
            auth_headers = get_api_headers(self.site)
            
            logger.info(f"=== INCIDENT API CALL DETAILS ===")
            logger.info(f"Site: {self.site}")
            logger.info(f"Server IP: {self.server_ip}")
            logger.info(f"Base URL: {self.base_url}")
            logger.info(f"Full URL: {url}")
            logger.info(f"Parameters: {params}")
            logger.info(f"Headers: {auth_headers}")
            logger.info(f"x-api-username: {auth_headers.get('x-api-username', 'Not set')}")
            logger.info(f"x-api-key: {'*' * 20}...")  # API 키 마스킹
            logger.info(f"Accept: {auth_headers.get('Accept', 'Not set')}")
            logger.info(f"Content-Type: {auth_headers.get('Content-Type', 'Not set')}")
            logger.info(f"Total headers count: {len(auth_headers)}")
            logger.info(f"Request Method: GET")
            logger.info(f"=================================")
            
            # API 호출
            logger.info(f"Making API call to: {url}")
            logger.info(f"Request timeout: 120 seconds (2 minutes)")
            logger.info(f"Starting API request...")
            
            response = requests.get(url, params=params, headers=auth_headers, timeout=120)
            
            logger.info(f"API request completed!")
            
            logger.info(f"=== API RESPONSE DETAILS ===")
            logger.info(f"Response Status Code: {response.status_code}")
            logger.info(f"Response Headers: {dict(response.headers)}")
            logger.info(f"Response URL: {response.url}")
            logger.info(f"Response Encoding: {response.encoding}")
            logger.info(f"Response Content Length: {len(response.content)}")
            logger.info(f"Response Elapsed Time: {response.elapsed.total_seconds():.2f} seconds")
            logger.info(f"=================================")
            
            if response.status_code == 200:
                # 응답 내용을 JSON으로 파싱
                try:
                    incidents = response.json()
                    logger.info(f"Successfully parsed JSON response with {len(incidents)} incidents")
                    
                    # JSON 파일로 저장
                    self._save_incidents_to_json(incidents, start_date, end_date)
                    
                    # 날짜 필터링 (API에서 제공하지 않는 경우 클라이언트 측에서 필터링)
                    filtered_incidents = self._filter_incidents_by_date(incidents, start_date, end_date)
                    logger.info(f"Filtered to {len(filtered_incidents)} incidents within date range")
                    
                    return True, filtered_incidents
                    
                except ValueError as e:
                    logger.error(f"Failed to parse JSON response: {str(e)}")
                    logger.error(f"Response content (first 500 chars): {response.text[:500]}")
                    return False, None
                    
            else:
                logger.error(f"Failed to fetch incidents from {self.site}: HTTP {response.status_code}")
                logger.error(f"Response content: {response.text}")
                return False, None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching incidents from {self.site}: {str(e)}")
            logger.error(f"Request exception type: {type(e).__name__}")
            return False, None
        except Exception as e:
            logger.error(f"Unexpected error fetching incidents from {self.site}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, None
    
    def _filter_incidents_by_date(self, incidents: List[Dict[str, Any]], start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """날짜 범위에 따라 incident를 필터링합니다."""
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            filtered_incidents = []
            
            for incident in incidents:
                incident_date = incident.get('Date')
                if incident_date:
                    try:
                        # 날짜 문자열을 datetime 객체로 변환
                        if isinstance(incident_date, str):
                            incident_dt = datetime.fromisoformat(incident_date.replace('Z', '+00:00'))
                        else:
                            # 이미 datetime 객체인 경우
                            incident_dt = incident_date
                        
                        # 날짜 범위 확인
                        if start_dt <= incident_dt <= end_dt:
                            filtered_incidents.append(incident)
                            
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid incident date format: {incident_date}, error: {e}")
                        # 날짜 파싱에 실패한 경우 포함 (데이터 검증 필요)
                        filtered_incidents.append(incident)
                else:
                    # 날짜가 없는 경우 포함 (데이터 검증 필요)
                    filtered_incidents.append(incident)
            
            return filtered_incidents
            
        except Exception as e:
            logger.error(f"Error filtering incidents by date: {str(e)}")
            return incidents  # 필터링 실패 시 모든 incident 반환
    
    def _save_incidents_to_json(self, incidents: List[Dict[str, Any]], start_date: str, end_date: str):
        """Incident 데이터를 JSON 파일로 저장합니다."""
        try:
            import json
            import os
            from datetime import datetime
            
            # data 디렉토리 생성
            data_dir = 'data'
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                logger.info(f"Created data directory: {data_dir}")
            
            # 파일명 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'incidents_{self.site}_{start_date}_{end_date}_{timestamp}.json'
            filepath = os.path.join(data_dir, filename)
            
            # JSON 데이터 준비
            json_data = {
                'metadata': {
                    'site': self.site,
                    'start_date': start_date,
                    'end_date': end_date,
                    'exported_at': datetime.now().isoformat(),
                    'total_incidents': len(incidents)
                },
                'incidents': incidents
            }
            
            # JSON 파일로 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"=== JSON FILE SAVED SUCCESSFULLY ===")
            logger.info(f"File path: {filepath}")
            logger.info(f"File size: {os.path.getsize(filepath)} bytes")
            logger.info(f"Total incidents saved: {len(incidents)}")
            logger.info(f"=====================================")
            
        except Exception as e:
            logger.error(f"Error saving incidents to JSON: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def _save_clients_to_json(self, clients: List[Dict[str, Any]], site: str):
        """클라이언트 데이터를 JSON 파일로 저장합니다."""
        try:
            import json
            import os
            from datetime import datetime
            
            # data 디렉토리 생성
            data_dir = 'data'
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
                logger.info(f"Created data directory: {data_dir}")
            
            # 파일명 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'clients_{site}_{timestamp}.json'
            filepath = os.path.join(data_dir, filename)
            
            # JSON 데이터 준비
            json_data = {
                'metadata': {
                    'site': site,
                    'exported_at': datetime.now().isoformat(),
                    'total_clients': len(clients)
                },
                'clients': clients
            }
            
            # JSON 파일로 저장
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)
            
            logger.info(f"=== CLIENTS JSON FILE SAVED SUCCESSFULLY ===")
            logger.info(f"File path: {filepath}")
            logger.info(f"File size: {os.path.getsize(filepath)} bytes")
            logger.info(f"Total clients saved: {len(clients)}")
            logger.info(f"===========================================")
            
        except Exception as e:
            logger.error(f"Error saving clients to JSON: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def fetch_clients(self) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """클라이언트 목록을 가져옵니다."""
        try:
            # 기존 클라이언트 API 사용
            from api_client import fetch_client_information
            
            success, clients = fetch_client_information(self.site)
            
            if success:
                logger.info(f"Successfully fetched {len(clients)} clients from {self.site}")
                return True, clients
            else:
                logger.error(f"Failed to fetch clients from {self.site}")
                return False, None
                
        except Exception as e:
            logger.error(f"Error fetching clients from {self.site}: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False, None

def fetch_incidents_with_client_data(site: str, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
    """Incident 데이터와 클라이언트 데이터를 함께 가져와서 매칭합니다."""
    try:
        logger.info(f"Fetching incidents with client data for {site} from {start_date} to {end_date}")
        
        # Incident API 초기화
        incident_api = IncidentAPI(site)
        
        # Incident 데이터 가져오기
        incidents_success, incidents = incident_api.fetch_incidents(start_date, end_date)
        if not incidents_success:
            logger.error(f"Failed to fetch incidents for {site}")
            return None
        
        # 클라이언트 데이터 가져오기
        clients_success, clients = incident_api.fetch_clients()
        if not clients_success:
            logger.error(f"Failed to fetch clients for {site}")
            return None
        
        # 클라이언트 데이터도 JSON으로 저장
        incident_api._save_clients_to_json(clients, site)
        
        # 데이터 매칭 및 가공
        processed_incidents = process_incident_data(incidents, clients)
        
        logger.info(f"Successfully processed {len(processed_incidents)} incidents for {site}")
        
        return {
            'incidents': processed_incidents,
            'clients': clients,
            'site': site,
            'period': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_incidents_with_client_data for {site}: {str(e)}")
        return None

def process_incident_data(incidents: List[Dict[str, Any]], clients: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Incident 데이터를 가공하고 클라이언트 정보와 매칭합니다."""
    try:
        processed_incidents = []
        
        for incident in incidents:
            # 클라이언트 정보 찾기
            client_id = incident.get('ClientId')
            matched_client = None
            
            if client_id:
                # PersonId 또는 MainClientServiceId로 매칭
                matched_client = next(
                    (client for client in clients 
                     if client.get('PersonId') == client_id or 
                        client.get('MainClientServiceId') == client_id),
                    None
                )
            
            # 가공된 incident 데이터 생성
            processed_incident = {
                'Id': incident.get('Id'),
                'ClientId': client_id,
                'Date': incident.get('Date'),
                'EventTypeNames': incident.get('EventTypeNames', []),
                'InjuryTypeNames': incident.get('InjuryTypeNames', []),
                'LocationName': incident.get('LocationName'),
                'AreaName': incident.get('AreaName'),
                'WingName': incident.get('WingName'),
                'RoomName': incident.get('RoomName'),
                'BedRoom': incident.get('BedRoom'),
                'DepartmentName': incident.get('DepartmentName'),
                'RiskRatingName': incident.get('RiskRatingName'),
                'ReportedByName': incident.get('ReportedByName'),
                'ReportedDate': incident.get('ReportedDate'),
                'ReportedToName': incident.get('ReportedToName'),
                'ReviewedByName': incident.get('ReviewedByName'),
                'ReviewedDate': incident.get('ReviewedDate'),
                'IsReviewClosed': incident.get('IsReviewClosed'),
                'WasInjurySustained': incident.get('WasInjurySustained'),
                'Description': incident.get('Description'),
                'ActionTaken': incident.get('ActionTaken'),
                'ReviewNotes': incident.get('ReviewNotes'),
                'Recommendations': incident.get('Recommendations'),
                'WitnessNames': incident.get('WitnessNames', []),
                'AdverseEventOrganisationFactorDetails': incident.get('AdverseEventOrganisationFactorDetails', []),
                'AdverseEventPersonnelFactorDetails': incident.get('AdverseEventPersonnelFactorDetails', []),
                'AdverseEventClientFactorDetails': incident.get('AdverseEventClientFactorDetails', []),
                'ActivityDuringFall': incident.get('ActivityDuringFall'),
                'IsFallPreventionInPlace': incident.get('IsFallPreventionInPlace'),
                'FallPreventionMethods': incident.get('FallPreventionMethods', []),
                'WoundRecordIds': incident.get('WoundRecordIds', []),
                'MedicationIssues': incident.get('MedicationIssues', []),
                'AllergicReactions': incident.get('AllergicReactions', []),
                'AdverseEventGeneralIssues': incident.get('AdverseEventGeneralIssues', []),
                'Communications': incident.get('Communications', []),
                'LastUpdatedDate': incident.get('LastUpdatedDate'),
                'MatchedClient': matched_client
            }
            
            processed_incidents.append(processed_incident)
        
        logger.info(f"Processed {len(processed_incidents)} incidents")
        return processed_incidents
        
    except Exception as e:
        logger.error(f"Error processing incident data: {str(e)}")
        return incidents  # 처리 실패 시 원본 데이터 반환

def get_incident_summary(incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Incident 데이터의 요약 통계를 생성합니다."""
    try:
        if not incidents:
            return {
                'total_incidents': 0,
                'risk_breakdown': {'high': 0, 'medium': 0, 'low': 0},
                'event_types': {},
                'injury_types': {},
                'locations': {}
            }
        
        # 위험도별 분류
        risk_breakdown = {'high': 0, 'medium': 0, 'low': 0}
        event_types = {}
        injury_types = {}
        locations = {}
        
        for incident in incidents:
            # 위험도 분류
            risk_rating = incident.get('RiskRatingName', '').lower()
            if 'high' in risk_rating or any(str(i) in risk_rating for i in range(5, 11)):
                risk_breakdown['high'] += 1
            elif 'medium' in risk_rating or any(str(i) in risk_rating for i in range(3, 5)):
                risk_breakdown['medium'] += 1
            else:
                risk_breakdown['low'] += 1
            
            # 이벤트 타입별 분류
            for event_type in incident.get('EventTypeNames', []):
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            # 부상 타입별 분류
            for injury_type in incident.get('InjuryTypeNames', []):
                injury_types[injury_type] = injury_types.get(injury_type, 0) + 1
            
            # 위치별 분류
            location = incident.get('LocationName') or incident.get('AreaName') or 'Unknown'
            locations[location] = locations.get(location, 0) + 1
        
        return {
            'total_incidents': len(incidents),
            'risk_breakdown': risk_breakdown,
            'event_types': event_types,
            'injury_types': injury_types,
            'locations': locations
        }
        
    except Exception as e:
        logger.error(f"Error generating incident summary: {str(e)}")
        return {
            'total_incidents': len(incidents),
            'risk_breakdown': {'high': 0, 'medium': 0, 'low': 0},
            'event_types': {},
            'injury_types': {},
            'locations': {}
        }
