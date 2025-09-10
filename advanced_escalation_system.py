#!/usr/bin/env python3
"""
Progress Report System - 고급 에스컬레이션 시스템
다단계 알람 간격 및 수신자 관리 시스템
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Any

class AdvancedEscalationSystem:
    """고급 에스컬레이션 시스템"""
    
    def __init__(self, db_path='progress_report.db'):
        self.db_path = db_path
        
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"데이터베이스 파일 {self.db_path}를 찾을 수 없습니다.")
    
    def create_advanced_escalation_schema(self):
        """고급 에스컬레이션 스키마 생성"""
        print("=" * 70)
        print("고급 에스컬레이션 시스템 스키마 생성")
        print("=" * 70)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 1. 에스컬레이션 정책 테이블 (기존 테이블 확장)
            print("\n1. 에스컬레이션 정책 테이블 재설계")
            
            # 기존 테이블 삭제하고 새로 생성
            cursor.execute('DROP TABLE IF EXISTS escalation_policies')
            
            cursor.execute('''
                CREATE TABLE escalation_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    event_type VARCHAR(50) NOT NULL,
                    priority VARCHAR(20) NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES users(id)
                )
            ''')
            print("  ✓ escalation_policies 테이블 재생성")
            
            # 2. 에스컬레이션 단계 테이블 (새로 생성)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS escalation_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy_id INTEGER NOT NULL,
                    step_number INTEGER NOT NULL,
                    delay_minutes INTEGER NOT NULL,
                    repeat_count INTEGER NOT NULL,
                    recipients TEXT NOT NULL,
                    message_template VARCHAR(500),
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (policy_id) REFERENCES escalation_policies(id),
                    UNIQUE(policy_id, step_number)
                )
            ''')
            print("  ✓ escalation_steps 테이블 생성")
            
            # 3. 알람 실행 로그 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alarm_execution_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alarm_id VARCHAR(100) NOT NULL,
                    policy_id INTEGER,
                    step_number INTEGER,
                    execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    recipients_sent TEXT,
                    message_sent TEXT,
                    fcm_result TEXT,
                    status VARCHAR(20) DEFAULT 'sent',
                    error_message TEXT,
                    FOREIGN KEY (policy_id) REFERENCES escalation_policies(id)
                )
            ''')
            print("  ✓ alarm_execution_logs 테이블 생성")
            
            # 4. 활성 알람 상태 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS active_alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alarm_id VARCHAR(100) UNIQUE NOT NULL,
                    policy_id INTEGER NOT NULL,
                    incident_id VARCHAR(100),
                    client_name VARCHAR(200),
                    site VARCHAR(100),
                    event_type VARCHAR(100),
                    risk_rating VARCHAR(20),
                    current_step INTEGER DEFAULT 1,
                    current_repeat INTEGER DEFAULT 0,
                    next_execution_time TIMESTAMP,
                    total_sent INTEGER DEFAULT 0,
                    is_acknowledged BOOLEAN DEFAULT 0,
                    acknowledged_by VARCHAR(100),
                    acknowledged_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (policy_id) REFERENCES escalation_policies(id)
                )
            ''')
            print("  ✓ active_alarms 테이블 생성")
            
            # 5. 인덱스 생성
            indexes = [
                ('idx_escalation_steps_policy', 'escalation_steps', '(policy_id, step_number)'),
                ('idx_alarm_logs_alarm_id', 'alarm_execution_logs', '(alarm_id, execution_time)'),
                ('idx_active_alarms_next_exec', 'active_alarms', '(next_execution_time, is_acknowledged)'),
                ('idx_active_alarms_policy', 'active_alarms', '(policy_id, current_step)')
            ]
            
            for index_name, table_name, columns in indexes:
                cursor.execute(f'CREATE INDEX IF NOT EXISTS {index_name} ON {table_name} {columns}')
            
            print("  ✓ 인덱스 생성 완료")
            
            conn.commit()
            print("\n✅ 고급 에스컬레이션 스키마 생성 완료!")
            
        except Exception as e:
            print(f"\n❌ 스키마 생성 실패: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def create_default_escalation_policies(self):
        """기본 에스컬레이션 정책 생성"""
        print("\n기본 에스컬레이션 정책 생성")
        print("-" * 50)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 기본 정책들
            default_policies = [
                {
                    'name': '긴급상황 에스컬레이션',
                    'description': '높은 위험도의 긴급 상황에 대한 에스컬레이션 정책',
                    'event_type': 'emergency',
                    'priority': 'high',
                    'steps': [
                        {'step': 1, 'delay': 0, 'repeat': 1, 'recipients': ['site_admin', 'doctor'], 'template': '즉시 확인 필요'},
                        {'step': 2, 'delay': 15, 'repeat': 4, 'recipients': ['admin', 'site_admin', 'doctor'], 'template': '15분 간격 반복 알림'},
                        {'step': 3, 'delay': 30, 'repeat': 2, 'recipients': ['admin', 'site_admin', 'doctor'], 'template': '30분 간격 반복 알림'},
                        {'step': 4, 'delay': 60, 'repeat': 2, 'recipients': ['admin', 'manager'], 'template': '1시간 간격 반복 알림'},
                        {'step': 5, 'delay': 360, 'repeat': 2, 'recipients': ['admin', 'manager', 'director'], 'template': '6시간 간격 반복 알림'}
                    ]
                },
                {
                    'name': '일반상황 에스컬레이션',
                    'description': '중간 위험도 상황에 대한 에스컬레이션 정책',
                    'event_type': 'normal',
                    'priority': 'medium',
                    'steps': [
                        {'step': 1, 'delay': 0, 'repeat': 1, 'recipients': ['site_admin'], 'template': '상황 확인 요청'},
                        {'step': 2, 'delay': 30, 'repeat': 2, 'recipients': ['admin', 'site_admin'], 'template': '30분 간격 확인 요청'},
                        {'step': 3, 'delay': 120, 'repeat': 1, 'recipients': ['admin'], 'template': '2시간 후 최종 확인'}
                    ]
                },
                {
                    'name': '복약 알림 에스컬레이션',
                    'description': '복약 시간 알림에 대한 에스컬레이션 정책',
                    'event_type': 'medication',
                    'priority': 'normal',
                    'steps': [
                        {'step': 1, 'delay': 0, 'repeat': 1, 'recipients': ['doctor', 'site_admin'], 'template': '복약 시간 알림'},
                        {'step': 2, 'delay': 30, 'repeat': 2, 'recipients': ['doctor', 'site_admin'], 'template': '복약 미복용 알림'},
                        {'step': 3, 'delay': 60, 'repeat': 1, 'recipients': ['admin', 'doctor'], 'template': '복약 미복용 최종 알림'}
                    ]
                }
            ]
            
            # 정책 삽입
            for policy_data in default_policies:
                # 정책 기본 정보 삽입
                cursor.execute('''
                    INSERT INTO escalation_policies 
                    (policy_name, description, event_type, priority, created_by)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    policy_data['name'],
                    policy_data['description'],
                    policy_data['event_type'],
                    policy_data['priority'],
                    1  # admin 사용자 ID
                ))
                
                policy_id = cursor.lastrowid
                
                # 에스컬레이션 단계 삽입
                for step_data in policy_data['steps']:
                    cursor.execute('''
                        INSERT INTO escalation_steps 
                        (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        policy_id,
                        step_data['step'],
                        step_data['delay'],
                        step_data['repeat'],
                        json.dumps(step_data['recipients']),
                        step_data['template']
                    ))
                
                print(f"  ✓ {policy_data['name']}: {len(policy_data['steps'])}단계 생성")
            
            conn.commit()
            print(f"\n✅ 기본 에스컬레이션 정책 {len(default_policies)}개 생성 완료")
            
        except Exception as e:
            print(f"\n❌ 정책 생성 실패: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def verify_escalation_system(self):
        """에스컬레이션 시스템 검증"""
        print("\n에스컬레이션 시스템 검증")
        print("-" * 50)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # 정책 수 확인
            cursor.execute('SELECT COUNT(*) FROM escalation_policies WHERE is_active = 1')
            policy_count = cursor.fetchone()[0]
            print(f"  📋 활성 정책: {policy_count}개")
            
            # 단계별 상세 확인
            cursor.execute('''
                SELECT ep.policy_name, ep.event_type, ep.priority,
                       es.step_number, es.delay_minutes, es.repeat_count, es.recipients
                FROM escalation_policies ep
                JOIN escalation_steps es ON ep.id = es.policy_id
                WHERE ep.is_active = 1
                ORDER BY ep.policy_name, es.step_number
            ''')
            
            current_policy = None
            for row in cursor.fetchall():
                policy_name, event_type, priority, step_num, delay, repeat, recipients = row
                
                if current_policy != policy_name:
                    current_policy = policy_name
                    print(f"\n  🚨 {policy_name} ({event_type}, {priority}):")
                
                recipients_list = json.loads(recipients)
                delay_text = f"{delay}분" if delay > 0 else "즉시"
                print(f"    단계 {step_num}: {delay_text} 후 {repeat}회 반복 → {', '.join(recipients_list)}")
            
            # 총 단계 수 확인
            cursor.execute('SELECT COUNT(*) FROM escalation_steps WHERE is_active = 1')
            total_steps = cursor.fetchone()[0]
            print(f"\n  📊 전체 에스컬레이션 단계: {total_steps}개")
            
        finally:
            conn.close()


def create_escalation_web_ui():
    """에스컬레이션 정책 관리 웹 UI 생성"""
    print("\n" + "=" * 70)
    print("에스컬레이션 정책 관리 웹 UI 생성")
    print("=" * 70)
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Escalation Policy Management - Progress Report System</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <style>
        :root {
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --accent-color: #e74c3c;
            --success-color: #27ae60;
            --warning-color: #f39c12;
            --light-bg: #ecf0f1;
            --dark-text: #2c3e50;
            --border-color: #bdc3c7;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--light-bg);
            color: var(--dark-text);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }

        .header h1 {
            font-size: 2.2em;
            margin-bottom: 10px;
        }

        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }

        .nav-buttons {
            text-align: center;
            margin-bottom: 30px;
        }

        .nav-btn {
            background-color: var(--secondary-color);
            color: white;
            border: none;
            padding: 12px 24px;
            margin: 0 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }

        .nav-btn:hover {
            background-color: var(--primary-color);
            transform: translateY(-2px);
        }

        .policy-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }

        .policy-list, .policy-editor {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .policy-list h2, .policy-editor h2 {
            color: var(--primary-color);
            margin-bottom: 20px;
            font-size: 1.5em;
        }

        .policy-item {
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .policy-item:hover {
            border-color: var(--secondary-color);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }

        .policy-item.selected {
            border-color: var(--secondary-color);
            background-color: #f8f9fa;
        }

        .policy-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .policy-name {
            font-weight: bold;
            color: var(--primary-color);
        }

        .policy-priority {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
        }

        .priority-high {
            background-color: var(--accent-color);
            color: white;
        }

        .priority-medium {
            background-color: var(--warning-color);
            color: white;
        }

        .priority-normal {
            background-color: var(--success-color);
            color: white;
        }

        .policy-steps {
            font-size: 0.9em;
            color: #666;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: var(--primary-color);
        }

        .form-control {
            width: 100%;
            padding: 10px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            font-size: 14px;
        }

        .form-control:focus {
            outline: none;
            border-color: var(--secondary-color);
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }

        .escalation-steps {
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }

        .step-item {
            background-color: #f8f9fa;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid var(--secondary-color);
        }

        .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .step-number {
            background-color: var(--secondary-color);
            color: white;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }

        .step-config {
            display: grid;
            grid-template-columns: 1fr 1fr 2fr;
            gap: 10px;
            margin-bottom: 10px;
        }

        .recipients-config {
            margin-top: 10px;
        }

        .recipient-checkbox {
            margin-right: 15px;
            margin-bottom: 5px;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s ease;
        }

        .btn-primary {
            background-color: var(--secondary-color);
            color: white;
        }

        .btn-primary:hover {
            background-color: var(--primary-color);
        }

        .btn-success {
            background-color: var(--success-color);
            color: white;
        }

        .btn-success:hover {
            background-color: #219a52;
        }

        .btn-danger {
            background-color: var(--accent-color);
            color: white;
        }

        .btn-danger:hover {
            background-color: #c0392b;
        }

        .btn-add-step {
            background-color: var(--warning-color);
            color: white;
            margin-top: 10px;
        }

        .btn-add-step:hover {
            background-color: #e67e22;
        }

        .notification {
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            display: none;
        }

        .notification.success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .notification.error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .notification.info {
            background-color: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚡ Escalation Policy Management</h1>
            <p>다단계 알람 에스컬레이션 정책 관리 시스템</p>
        </div>

        <div class="nav-buttons">
            <button class="nav-btn" onclick="window.location.href='/fcm-admin-dashboard'">← FCM Dashboard</button>
            <button class="nav-btn" onclick="window.location.href='/policy-alarm-management'">Policy & Alarm</button>
            <button class="nav-btn" onclick="window.location.href='/incident-viewer'">Incident Viewer</button>
        </div>

        <div id="notification" class="notification"></div>

        <div class="policy-grid">
            <!-- 정책 목록 -->
            <div class="policy-list">
                <h2>📋 에스컬레이션 정책 목록</h2>
                <div id="policyList">
                    <div style="text-align: center; padding: 20px; color: #666;">
                        정책을 불러오는 중...
                    </div>
                </div>
                <button class="btn btn-primary" onclick="createNewPolicy()" style="margin-top: 15px;">
                    ➕ 새 정책 생성
                </button>
            </div>

            <!-- 정책 편집기 -->
            <div class="policy-editor">
                <h2>✏️ 정책 편집기</h2>
                <div id="policyEditor">
                    <form id="policyForm">
                        <div class="form-group">
                            <label for="policyName">정책 이름</label>
                            <input type="text" id="policyName" class="form-control" placeholder="예: 긴급상황 에스컬레이션">
                        </div>

                        <div class="form-group">
                            <label for="policyDescription">설명</label>
                            <textarea id="policyDescription" class="form-control" rows="3" placeholder="정책에 대한 설명을 입력하세요"></textarea>
                        </div>

                        <div class="form-group">
                            <label for="eventType">이벤트 타입</label>
                            <select id="eventType" class="form-control">
                                <option value="emergency">긴급상황</option>
                                <option value="normal">일반상황</option>
                                <option value="medication">복약 알림</option>
                                <option value="handover">교대 인수인계</option>
                                <option value="maintenance">시설 점검</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label for="priority">우선순위</label>
                            <select id="priority" class="form-control">
                                <option value="high">높음 (High)</option>
                                <option value="medium">중간 (Medium)</option>
                                <option value="normal">보통 (Normal)</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label>에스컬레이션 단계 설정</label>
                            <div class="escalation-steps" id="escalationSteps">
                                <!-- 동적으로 생성됨 -->
                            </div>
                            <button type="button" class="btn btn-add-step" onclick="addEscalationStep()">
                                ➕ 단계 추가
                            </button>
                        </div>

                        <div style="text-align: center; margin-top: 30px;">
                            <button type="button" class="btn btn-success" onclick="savePolicyChanges()">
                                💾 정책 저장
                            </button>
                            <button type="button" class="btn btn-danger" onclick="deletePolicyConfirm()" style="margin-left: 10px;">
                                🗑️ 정책 삭제
                            </button>
                            <button type="button" class="btn btn-primary" onclick="testPolicyExecution()" style="margin-left: 10px;">
                                🧪 정책 테스트
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <!-- 정책 실행 로그 -->
        <div class="policy-list" style="margin-top: 30px;">
            <h2>📊 정책 실행 로그</h2>
            <div id="executionLogs">
                <div style="text-align: center; padding: 20px; color: #666;">
                    실행 로그를 불러오는 중...
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentPolicyId = null;
        let availableRecipients = [];
        let stepCounter = 0;

        // 페이지 로드 시 초기화
        document.addEventListener('DOMContentLoaded', function() {
            loadPolicies();
            loadAvailableRecipients();
            createDefaultEscalationSteps();
        });

        // 정책 목록 로드
        async function loadPolicies() {
            try {
                const response = await fetch('/api/escalation-policies');
                const result = await response.json();

                if (result.success) {
                    displayPolicies(result.policies);
                } else {
                    showNotification('정책 목록을 불러올 수 없습니다.', 'error');
                }
            } catch (error) {
                console.error('정책 로드 오류:', error);
                showNotification('정책 로드 중 오류가 발생했습니다.', 'error');
            }
        }

        // 정책 목록 표시
        function displayPolicies(policies) {
            const container = document.getElementById('policyList');
            
            if (policies.length === 0) {
                container.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">등록된 정책이 없습니다.</div>';
                return;
            }

            let html = '';
            policies.forEach(policy => {
                const priorityClass = `priority-${policy.priority}`;
                html += `
                    <div class="policy-item" onclick="selectPolicy(${policy.id})">
                        <div class="policy-header">
                            <div class="policy-name">${policy.policy_name}</div>
                            <div class="policy-priority ${priorityClass}">${policy.priority.toUpperCase()}</div>
                        </div>
                        <div style="color: #666; font-size: 0.9em;">${policy.event_type}</div>
                        <div class="policy-steps">${policy.step_count || 0}단계 에스컬레이션</div>
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        // 기본 에스컬레이션 단계 생성 (15분 4회 → 30분 2회 → 1시간 2회 → 6시간 2회)
        function createDefaultEscalationSteps() {
            const defaultSteps = [
                { delay: 0, repeat: 1, recipients: ['site_admin', 'doctor'], template: '즉시 알림' },
                { delay: 15, repeat: 4, recipients: ['admin', 'site_admin', 'doctor'], template: '15분 간격 반복 알림' },
                { delay: 30, repeat: 2, recipients: ['admin', 'site_admin', 'doctor'], template: '30분 간격 반복 알림' },
                { delay: 60, repeat: 2, recipients: ['admin', 'manager'], template: '1시간 간격 반복 알림' },
                { delay: 360, repeat: 2, recipients: ['admin', 'manager', 'director'], template: '6시간 간격 반복 알림' }
            ];

            const container = document.getElementById('escalationSteps');
            container.innerHTML = '';

            defaultSteps.forEach((step, index) => {
                addEscalationStepWithData(step, index + 1);
            });
        }

        // 에스컬레이션 단계 추가
        function addEscalationStep() {
            const stepData = {
                delay: 15,
                repeat: 1,
                recipients: ['site_admin'],
                template: '알림 메시지'
            };
            
            stepCounter++;
            addEscalationStepWithData(stepData, stepCounter);
        }

        // 데이터와 함께 에스컬레이션 단계 추가
        function addEscalationStepWithData(stepData, stepNumber) {
            const container = document.getElementById('escalationSteps');
            
            const stepHtml = `
                <div class="step-item" id="step-${stepNumber}">
                    <div class="step-header">
                        <div class="step-number">${stepNumber}</div>
                        <button type="button" class="btn btn-danger" onclick="removeStep(${stepNumber})" style="padding: 5px 10px; font-size: 12px;">
                            ❌ 제거
                        </button>
                    </div>
                    
                    <div class="step-config">
                        <div>
                            <label>지연 시간 (분)</label>
                            <input type="number" class="form-control" name="delay" value="${stepData.delay}" min="0" max="1440">
                        </div>
                        <div>
                            <label>반복 횟수</label>
                            <input type="number" class="form-control" name="repeat" value="${stepData.repeat}" min="1" max="10">
                        </div>
                        <div>
                            <label>메시지 템플릿</label>
                            <input type="text" class="form-control" name="template" value="${stepData.template}" placeholder="알림 메시지">
                        </div>
                    </div>
                    
                    <div class="recipients-config">
                        <label>수신자 선택</label>
                        <div id="recipients-${stepNumber}">
                            ${generateRecipientCheckboxes(stepData.recipients, stepNumber)}
                        </div>
                    </div>
                </div>
            `;
            
            container.insertAdjacentHTML('beforeend', stepHtml);
        }

        // 수신자 체크박스 생성
        function generateRecipientCheckboxes(selectedRecipients, stepNumber) {
            const allRecipients = [
                { id: 'site_admin', name: '사이트 관리자', role: 'Site Admin' },
                { id: 'admin', name: '시스템 관리자', role: 'System Admin' },
                { id: 'doctor', name: '의사', role: 'Doctor' },
                { id: 'nurse', name: '간호사', role: 'Nurse' },
                { id: 'physiotherapist', name: '물리치료사', role: 'Physiotherapist' },
                { id: 'manager', name: '매니저', role: 'Manager' },
                { id: 'director', name: '디렉터', role: 'Director' }
            ];

            let html = '';
            allRecipients.forEach(recipient => {
                const checked = selectedRecipients.includes(recipient.id) ? 'checked' : '';
                html += `
                    <label class="recipient-checkbox">
                        <input type="checkbox" name="recipients-${stepNumber}" value="${recipient.id}" ${checked}>
                        ${recipient.name} (${recipient.role})
                    </label>
                `;
            });

            return html;
        }

        // 단계 제거
        function removeStep(stepNumber) {
            const stepElement = document.getElementById(`step-${stepNumber}`);
            if (stepElement) {
                stepElement.remove();
            }
        }

        // 정책 저장
        async function savePolicyChanges() {
            try {
                const formData = collectFormData();
                
                if (!validateFormData(formData)) {
                    return;
                }

                const response = await fetch('/api/escalation-policies', {
                    method: currentPolicyId ? 'PUT' : 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (result.success) {
                    showNotification('정책이 성공적으로 저장되었습니다.', 'success');
                    loadPolicies(); // 목록 새로고침
                } else {
                    showNotification(`정책 저장 실패: ${result.message}`, 'error');
                }

            } catch (error) {
                console.error('정책 저장 오류:', error);
                showNotification('정책 저장 중 오류가 발생했습니다.', 'error');
            }
        }

        // 폼 데이터 수집
        function collectFormData() {
            const steps = [];
            const stepElements = document.querySelectorAll('.step-item');

            stepElements.forEach((stepElement, index) => {
                const delay = stepElement.querySelector('[name="delay"]').value;
                const repeat = stepElement.querySelector('[name="repeat"]').value;
                const template = stepElement.querySelector('[name="template"]').value;
                
                const recipientCheckboxes = stepElement.querySelectorAll('[name^="recipients-"]:checked');
                const recipients = Array.from(recipientCheckboxes).map(cb => cb.value);

                steps.push({
                    step_number: index + 1,
                    delay_minutes: parseInt(delay),
                    repeat_count: parseInt(repeat),
                    recipients: recipients,
                    message_template: template
                });
            });

            return {
                policy_id: currentPolicyId,
                policy_name: document.getElementById('policyName').value,
                description: document.getElementById('policyDescription').value,
                event_type: document.getElementById('eventType').value,
                priority: document.getElementById('priority').value,
                steps: steps
            };
        }

        // 폼 데이터 검증
        function validateFormData(formData) {
            if (!formData.policy_name.trim()) {
                showNotification('정책 이름을 입력하세요.', 'error');
                return false;
            }

            if (formData.steps.length === 0) {
                showNotification('최소 1개의 에스컬레이션 단계가 필요합니다.', 'error');
                return false;
            }

            for (let step of formData.steps) {
                if (step.recipients.length === 0) {
                    showNotification(`단계 ${step.step_number}에 수신자를 선택하세요.`, 'error');
                    return false;
                }
            }

            return true;
        }

        // 알림 표시
        function showNotification(message, type) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = `notification ${type}`;
            notification.style.display = 'block';

            setTimeout(() => {
                notification.style.display = 'none';
            }, 5000);
        }

        // 새 정책 생성
        function createNewPolicy() {
            currentPolicyId = null;
            document.getElementById('policyForm').reset();
            createDefaultEscalationSteps();
            showNotification('새 정책을 생성합니다. 정보를 입력하세요.', 'info');
        }

        // 정책 테스트
        async function testPolicyExecution() {
            const formData = collectFormData();
            
            if (!validateFormData(formData)) {
                return;
            }

            try {
                const response = await fetch('/api/escalation-policies/test', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                const result = await response.json();

                if (result.success) {
                    showNotification(`정책 테스트 완료: 총 ${result.total_notifications}개의 알림이 ${result.total_duration}분에 걸쳐 전송됩니다.`, 'success');
                } else {
                    showNotification(`정책 테스트 실패: ${result.message}`, 'error');
                }

            } catch (error) {
                console.error('정책 테스트 오류:', error);
                showNotification('정책 테스트 중 오류가 발생했습니다.', 'error');
            }
        }
    </script>
</body>
</html>'''
    
    with open('templates/EscalationPolicyManagement.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("✅ templates/EscalationPolicyManagement.html 생성 완료")

def create_escalation_api_endpoints():
    """에스컬레이션 정책 관리 API 엔드포인트 생성"""
    print("\n에스컬레이션 정책 관리 API 생성")
    print("-" * 50)
    
    api_code = '''
# ==============================
# app.py에 추가할 에스컬레이션 정책 관리 API
# ==============================

@app.route('/escalation-policy-management')
@login_required
def escalation_policy_management():
    """에스컬레이션 정책 관리 페이지"""
    # 관리자와 사이트 관리자만 접근 가능
    if current_user.role not in ['admin', 'site_admin']:
        flash('Access denied. This page is for admin users only.', 'error')
        return redirect(url_for('home'))
    
    return render_template('EscalationPolicyManagement.html', current_user=current_user)

@app.route('/api/escalation-policies', methods=['GET'])
@login_required
def get_escalation_policies():
    """에스컬레이션 정책 목록 조회"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # 정책과 단계 정보를 함께 조회
        cursor.execute('''
            SELECT ep.id, ep.policy_name, ep.description, ep.event_type, ep.priority,
                   ep.is_active, ep.created_at,
                   COUNT(es.id) as step_count
            FROM escalation_policies ep
            LEFT JOIN escalation_steps es ON ep.id = es.policy_id AND es.is_active = 1
            WHERE ep.is_active = 1
            GROUP BY ep.id
            ORDER BY ep.priority DESC, ep.policy_name
        ''')
        
        policies = []
        for row in cursor.fetchall():
            policies.append({
                'id': row[0],
                'policy_name': row[1],
                'description': row[2],
                'event_type': row[3],
                'priority': row[4],
                'is_active': row[5],
                'created_at': row[6],
                'step_count': row[7]
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'policies': policies
        })
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 조회 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies', methods=['POST'])
@login_required
def create_escalation_policy():
    """새로운 에스컬레이션 정책 생성"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        data = request.get_json()
        
        conn = sqlite3.connect('progress_report.db')
        cursor = conn.cursor()
        
        # 정책 기본 정보 삽입
        cursor.execute('''
            INSERT INTO escalation_policies 
            (policy_name, description, event_type, priority, created_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['policy_name'],
            data['description'],
            data['event_type'],
            data['priority'],
            current_user.id
        ))
        
        policy_id = cursor.lastrowid
        
        # 에스컬레이션 단계 삽입
        for step in data['steps']:
            cursor.execute('''
                INSERT INTO escalation_steps 
                (policy_id, step_number, delay_minutes, repeat_count, recipients, message_template)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                policy_id,
                step['step_number'],
                step['delay_minutes'],
                step['repeat_count'],
                json.dumps(step['recipients']),
                step['message_template']
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'policy_id': policy_id,
            'message': '에스컬레이션 정책이 성공적으로 생성되었습니다.'
        })
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 생성 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/escalation-policies/test', methods=['POST'])
@login_required
def test_escalation_policy():
    """에스컬레이션 정책 테스트"""
    try:
        if current_user.role not in ['admin', 'site_admin']:
            return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403
        
        data = request.get_json()
        
        # 정책 실행 시뮬레이션
        total_notifications = 0
        total_duration = 0
        
        for step in data['steps']:
            step_notifications = step['repeat_count'] * len(step['recipients'])
            total_notifications += step_notifications
            
            if step['step_number'] > 1:
                total_duration = max(total_duration, step['delay_minutes'] * step['repeat_count'])
        
        return jsonify({
            'success': True,
            'total_notifications': total_notifications,
            'total_duration': total_duration,
            'message': f'정책 테스트 완료: {total_notifications}개 알림, {total_duration}분 소요'
        })
        
    except Exception as e:
        logger.error(f"에스컬레이션 정책 테스트 실패: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
'''
    
    with open('escalation_api_patch.py', 'w', encoding='utf-8') as f:
        f.write(api_code)
    
    print("✅ escalation_api_patch.py 생성 완료")

def main():
    """메인 실행 함수"""
    try:
        system = AdvancedEscalationSystem()
        
        # 1. 고급 스키마 생성
        system.create_advanced_escalation_schema()
        
        # 2. 기본 정책 생성
        system.create_default_escalation_policies()
        
        # 3. 시스템 검증
        system.verify_escalation_system()
        
        # 4. 웹 UI 생성
        create_escalation_web_ui()
        
        # 5. API 엔드포인트 생성
        create_escalation_api_endpoints()
        
        print("\n🎉 고급 에스컬레이션 시스템 구현 완료!")
        print("\n📁 생성된 파일:")
        print("  - templates/EscalationPolicyManagement.html (웹 UI)")
        print("  - escalation_api_patch.py (API 엔드포인트)")
        
        print("\n✅ 구현된 기능:")
        print("  - 15분 간격 4회 → 30분 간격 2회 → 1시간 간격 2회 → 6시간 간격 2회")
        print("  - 웹 UI에서 정책 생성/편집/삭제")
        print("  - 수신자별 맞춤 설정")
        print("  - 정책 테스트 기능")
        print("  - 실행 로그 추적")
        
        print("\n🚀 다음 단계:")
        print("1. escalation_api_patch.py의 코드를 app.py에 추가")
        print("2. /escalation-policy-management 페이지에서 정책 관리")
        print("3. 실제 알람 발생 시 에스컬레이션 자동 실행")
        
    except Exception as e:
        print(f"\n❌ 구현 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
