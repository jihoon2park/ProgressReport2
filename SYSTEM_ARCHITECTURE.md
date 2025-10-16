# Progress Report - System Architecture

## 🏗️ System Separation Overview

The Progress Report system has been separated into two independent systems for better maintainability, performance, and development workflow.

## 📋 System Structure

```
📁 ProgressReport/
├── 🏥 Core System (Port 5000)
│   ├── app.py                    # Main application
│   ├── templates/
│   │   ├── RODDashboard.html     # ROD management
│   │   ├── ProgressNoteList.html # Progress notes
│   │   └── UsageLogViewer.html   # Usage analytics
│   └── static/
│
├── 🛡️ Admin System (Port 5001)
│   ├── admin_app.py              # Admin application
│   ├── templates/
│   │   ├── incident_viewer.html  # Incident management
│   │   ├── policy_management.html # Policy configuration
│   │   └── fcm_dashboard.html    # FCM notifications
│   └── static/
│
├── 🔗 Shared Modules
│   ├── auth.py                   # Authentication system
│   ├── models.py                 # Data models
│   ├── usage_logger.py           # Logging system
│   └── config.py                 # Configuration
│
└── 📊 Common Data
    ├── progress_report.db        # SQLite database
    └── data/                     # JSON data files
```

## 🏥 Core System (Port 5000)

**Purpose**: Daily operations and resident care management

**Features**:
- ✅ ROD Dashboard - Residence of Day management
- ✅ Progress Notes - Clinical note taking and management
- ✅ Usage Log Viewer - System usage analytics
- ✅ Basic user authentication and session management

**Access URL**: http://127.0.0.1:5000

**Target Users**:
- Doctors, Physiotherapists, Care staff
- ROD users (ROD, YKROD, PGROD, etc.)
- General clinical staff

## 🛡️ Admin System (Port 5001)

**Purpose**: System administration and incident management

**Features**:
- ✅ Incident Viewer - Real-time incident monitoring
- ✅ Policy Management - Escalation policy configuration
- ✅ FCM Dashboard - Push notification management
- ✅ Advanced admin controls

**Access URL**: http://127.0.0.1:5001

**Target Users**:
- System administrators (admin role)
- Site administrators (site_admin role)
- IT support staff

## 🔐 Authentication & Authorization

### Shared Authentication
Both systems use the same authentication backend:
- **User Database**: `data/users/users.json`
- **Session Management**: Flask-Login with shared secret
- **Role-Based Access**: admin, site_admin, doctor, physiotherapist

### Access Control
- **Core System**: All authenticated users
- **Admin System**: Only admin and site_admin roles

## 🚀 Starting the Systems

### Option 1: Start Both Systems
```bash
# Windows
start_both_systems.bat

# This will open both systems in separate command windows
```

### Option 2: Start Individual Systems
```bash
# Core System only
start_core_system.bat
# or
python app.py

# Admin System only
start_admin_system.bat
# or
cd admin_system && python admin_app.py
```

## 🔄 System Communication

### Cross-System Navigation
- **From Core to Admin**: Links to http://127.0.0.1:5001
- **From Admin to Core**: Links to http://127.0.0.1:5000
- **Shared Database**: Both systems access the same SQLite database
- **Shared Logging**: Common usage logging system

### Data Synchronization
- **Database**: Shared SQLite database (`progress_report.db`)
- **User Data**: Shared user authentication system
- **Logs**: Common logging directory (`logs/`)
- **Static Files**: Each system has its own static assets

## 📊 Benefits of Separation

### 🎯 Development Benefits
- **Independent Development**: Teams can work on different systems simultaneously
- **Focused Codebase**: Each system contains only relevant functionality
- **Easier Testing**: Smaller, more focused test suites
- **Reduced Complexity**: Cleaner code organization

### ⚡ Performance Benefits
- **Faster Startup**: Each system loads only necessary components
- **Better Resource Usage**: Memory and CPU usage optimized per system
- **Scalability**: Systems can be scaled independently
- **Maintenance**: Updates can be deployed to specific systems

### 🛡️ Security Benefits
- **Isolation**: Admin functions isolated from daily operations
- **Access Control**: Granular permission system
- **Audit Trail**: Separate logging for different system types
- **Risk Reduction**: Issues in one system don't affect the other

## 🔧 Configuration

### Environment Variables
```bash
# Core System
CORE_PORT=5000
CORE_DEBUG=True

# Admin System  
ADMIN_PORT=5001
ADMIN_DEBUG=True

# Shared
SECRET_KEY=your-secret-key
DATABASE_PATH=./progress_report.db
```

### Database Configuration
Both systems share the same database configuration:
- **Path**: `progress_report.db`
- **Type**: SQLite
- **Migrations**: Handled by the core system

## 🚨 Troubleshooting

### Port Conflicts
If ports 5000 or 5001 are in use:
1. Check running processes: `netstat -ano | findstr :5000`
2. Kill conflicting processes or change ports in config files

### Database Access Issues
- Ensure `progress_report.db` exists in the project root
- Check file permissions
- Verify SQLite installation

### Authentication Problems
- Verify `data/users/users.json` exists and is readable
- Check user roles and permissions
- Clear browser cookies if sessions are stuck

## 📈 Future Enhancements

### Planned Features
- **API Gateway**: Unified API endpoint for both systems
- **Single Sign-On**: Enhanced authentication flow
- **Microservices**: Further system decomposition
- **Docker Support**: Containerized deployment
- **Load Balancing**: High availability setup

### Migration Path
The current separation provides a foundation for:
1. **Containerization**: Each system can be dockerized independently
2. **Cloud Deployment**: Systems can be deployed to different cloud services
3. **API-First Architecture**: RESTful APIs for system integration
4. **Third-Party Integration**: Easier integration with external systems

## 📞 Support

For system-related issues:
1. **Core System Issues**: Check core system logs in `logs/`
2. **Admin System Issues**: Check admin system logs
3. **Authentication Issues**: Verify user data and permissions
4. **Database Issues**: Check SQLite database integrity

---

**Last Updated**: October 1, 2025  
**Version**: 2.0.0 (System Separation Release)
