# Progress Report System

## 🏥 Overview

The Progress Report System is a comprehensive healthcare management platform designed for aged care facilities. It provides real-time progress note management, incident tracking (CIMS), policy management, and FCM (Firebase Cloud Messaging) notifications. 

**The system primarily uses direct SQL Server database access** for real-time data retrieval from MANAD Plus, with API integration available as a backup/fallback option when direct database access is unavailable.

## 🚀 Technology Stack

### Backend Framework
- **Flask 3.1.1** - Web application framework
- **Flask-Login 0.6.3** - User session management
- **Flask-SQLAlchemy 3.1.1** - Database ORM
- **SQLite** - Primary database with hybrid caching
- **Python 3.11+** - Core programming language
- **pyodbc** - SQL Server database connectivity
- **IIS + wfastcgi** - Production web server (Windows)

### Frontend Technologies
- **HTML5/CSS3** - User interface
- **JavaScript (ES6+)** - Client-side functionality
- **Chart.js** - Data visualization
- **IndexedDB** - Client-side data caching
- **Responsive Design** - Mobile-friendly interface

### External Services & APIs
- **Firebase Admin SDK 6.4.0** - Push notifications
- **RESTful APIs** - External data integration
- **Requests 2.32.3** - HTTP client for API calls
- **MANAD Plus Integration** - Direct SQL Server database access

### Additional Libraries
- **wfastcgi** - WSGI interface for IIS (Windows production)
- **Schedule 1.2.0** - Background task scheduling
- **Python-dotenv 1.1.0** - Environment configuration

## 🏗️ System Architecture

### Data Access Modes

The system uses **Direct Database Access** as the primary method, with API as a backup/fallback option.

#### 1. **Direct Database Access Mode** (Primary/Default)
- **Primary method** for data retrieval
- Direct connection to MANAD Plus SQL Server databases
- Real-time data retrieval without API overhead
- No API keys required
- Better performance and data accuracy
- Configured via `USE_DB_DIRECT_ACCESS=true` in `system_settings` table
- Uses `manad_db_connector.py` for READ-ONLY database access

#### 2. **API Mode** (Backup/Fallback Only)
- **Backup method** when direct DB access is unavailable
- RESTful API integration with MANAD Plus
- API key authentication required
- Configured via `USE_DB_DIRECT_ACCESS=false`
- API keys stored in `data/api_keys/api_keys.json`
- Used only when DB direct access fails or is disabled

### Core Components

#### 1. **Web Application Layer**
```
Flask Application (app.py)
├── Authentication & Authorization
├── Route Management
├── Session Handling
├── API Endpoints
└── Background Processors
```

#### 2. **Data Management Layer**
```
Primary Data Architecture:
├── MANAD Plus SQL Server (Direct Access - Primary)
│   ├── Progress Notes (Real-time)
│   ├── Adverse Events (Incidents)
│   ├── Client Information
│   └── Activity Events
│   └── READ-ONLY access via manad_db_connector.py
├── SQLite Database (Local Cache & System Data)
│   ├── Users & Authentication
│   ├── Client Data Cache
│   ├── Progress Notes Cache (Backup)
│   ├── CIMS Incidents (Synced)
│   ├── FCM Tokens
│   └── System Settings
└── JSON Files (Configuration)
    ├── API Keys (Backup mode only)
    └── Site Configuration (DB connection settings)
```

#### 3. **Caching System**
```
Caching Strategy (DB Direct Access Mode):
├── Level 1: Direct SQL Server Access (Real-time, Primary)
│   └── Always fresh data, no cache needed
├── Level 2: SQLite Cache (Backup/Sync data)
│   └── Used for CIMS incident synchronization
└── Level 3: IndexedDB (Client-side, optional)
    └── Browser-side caching for offline support

Note: In DB Direct Access mode, caching is minimal as data is always real-time.
API mode (backup) uses traditional caching strategies.
```

## 📊 Database Schema

### Core Tables
- **users** - User authentication and roles
- **fcm_tokens** - Firebase device tokens
- **access_logs** - User activity tracking
- **progress_note_logs** - Progress note audit trail
- **clients_cache** - Client data cache
- **cims_incidents** - Incident records synced from MANAD Plus
- **cims_tasks** - Policy-based tasks for incidents
- **system_settings** - System configuration (e.g., USE_DB_DIRECT_ACCESS)
- **api_keys** - API credentials (when using API mode)

### Performance Optimizations
- **Strategic Indexes** for fast queries
- **Composite Indexes** for complex searches
- **Query Optimization** for sub-10ms response times

## 🎯 Key Features

### 1. **Progress Note Management**
- Real-time progress note creation and editing
- Hybrid caching for instant data access
- Pagination with 50/100 items per page
- Advanced search and filtering
- Client-side IndexedDB caching
- Direct database access or API integration

### 2. **Incident Management (CIMS)**
- Real-time incident tracking from MANAD Plus
- Policy-based escalation (15min → 30min → 1hr → 6hr)
- FCM notification integration
- Admin dashboard for incident oversight
- Automatic task generation based on policies
- Status tracking (Open, In Progress, Closed)

### 3. **Dashboard Systems**

#### **Edenfield Dashboard**
- Company-wide statistics overview
- Site-by-site breakdown (5 sites)
- Resident counts and activity tracking
- Incident status overview
- Progress notes and activity types
- Period filtering (Today, This Week, This Month)

#### **Integrated Dashboard (CIMS)**
- Real-time incident KPIs
- Open/In Progress/Closed incident counts
- Falls tracking
- Site analysis with charts
- Event type distribution
- Risk and severity rating analysis

#### **ROD Dashboard**
- Residence of Day management
- Monthly and yearly views
- Activity tracking

### 4. **Policy Management**
- Web-based policy editing
- Escalation timeline configuration
- Recipient management via FCM tokens
- Real-time policy updates
- Automatic task generation

### 5. **FCM Admin Dashboard**
- Device token management
- Push notification testing
- Client synchronization status
- Token registration/removal

### 6. **User Management**
- Role-based access control (Admin, Site Admin, Doctor, Physiotherapist, Operations)
- Multi-site support
- Session management
- Custom landing pages per user
- Activity logging

### 7. **Data Access Configuration**
- **Direct DB Access Mode**: Fast, real-time data from SQL Server
- **API Mode**: RESTful API integration with authentication
- Automatic fallback between modes
- Configuration via database or environment variables

## 🔧 Installation & Setup

### Prerequisites
- **Windows Server** (IIS 8.0+) or **Linux Server**
- **Python 3.11+**
- **SQLite 3.x**
- **SQL Server** (for MANAD Plus direct access)
- **ODBC Driver 17 for SQL Server** (for Windows)
- **IIS with FastCGI module** (Windows production)
- **wfastcgi** package (Windows production)
- Modern web browser with IndexedDB support

### Installation Steps

1. **Clone Repository**
```bash
git clone https://github.com/jihoon2park/ProgressReport2.git
cd ProgressReport
```

2. **Create Virtual Environment**
```bash
python -m venv venv
```

3. **Activate Virtual Environment**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Install Dependencies**
```bash
pip install -r requirements.txt
pip install pyodbc  # Additional dependency for SQL Server
```

5. **Database Initialization**
```bash
python init_database.py
```

6. **Configure Data Access Mode**

   **Direct Database Access (Default/Primary)**
   ```python
   # Set in system_settings table (default is DB direct access)
   USE_DB_DIRECT_ACCESS = true
   ```
   - This is the **primary and recommended** method
   - No API keys required
   - Real-time data from SQL Server

   **API Mode (Backup Only)**
   ```python
   # Set in system_settings table (only if DB access unavailable)
   USE_DB_DIRECT_ACCESS = false
   # Configure API keys in data/api_keys/api_keys.json
   ```
   - Use only when direct DB access is not possible
   - Requires API keys configuration

7. **Configure Site Database Connections**

   For direct database access, configure site databases in `data/api_keys/site_config.json`:
   ```json
   [
     {
       "site_name": "Parafield Gardens",
       "database": {
         "server": "efsvr02\\sqlexpress",
         "database": "ManadPlus_Edenfield",
         "use_windows_auth": true
       }
     }
   ]
   ```

8. **Run Application**

   **Development:**
   ```bash
   python app.py
   ```

   **Production (Windows IIS):**
   ```bash
   # Deploy using deploy_iis.bat script
   deploy_iis.bat
   ```

   **Production (Linux):**
   ```bash
   gunicorn -c gunicorn.conf.py app:app
   ```

## 🚀 Performance Metrics

### Current Performance
- **Average Query Time**: <10ms
- **Cache Hit Rate**: 95%+
- **Database Size**: Optimized
- **Concurrent Users**: 50+ (tested)
- **Direct DB Access**: Real-time data retrieval

## 📱 User Interface

### Main Pages

1. **Progress Note List** (`/progress-notes`)
   - Paginated progress notes display
   - Real-time search and filtering
   - Cache refresh functionality
   - Admin controls

2. **Progress Note Editor** (`/`)
   - Client selection with search
   - Care area and event type dropdowns
   - Rich text editor for notes
   - Auto-save functionality

3. **Edenfield Dashboard** (`/edenfield-dashboard`)
   - Company-wide statistics
   - Site-by-site breakdown
   - Period filtering (Today/Week/Month)
   - Activity type analysis

4. **Integrated Dashboard** (`/integrated_dashboard`)
   - CIMS incident KPIs
   - Real-time incident tracking
   - Site analysis charts
   - Event type distribution

5. **ROD Dashboard** (`/rod-dashboard`)
   - Residence of Day management
   - Monthly/yearly views
   - Activity tracking

6. **Incident Viewer** (`/incident-viewer`)
   - Real-time incident monitoring
   - Policy management interface
   - Escalation timeline visualization

7. **FCM Admin Dashboard** (`/fcm-admin-dashboard`)
   - Device token management
   - Notification testing
   - Client sync status

8. **Admin Settings** (`/admin-settings`)
   - API key management
   - System configuration
   - Data source mode switching
   - Log viewer access

9. **User Management** (`/user-management`)
   - User creation and editing
   - Role assignment
   - Custom landing page configuration
   - Multi-site access control

## 🔐 Security Features

### Authentication & Authorization
- **Flask-Login** session management
- **Role-based access control** (RBAC)
- **Password hashing** with secure algorithms
- **Session timeout** protection
- **Custom landing pages** per user

### Data Security
- **API key management** (JSON-based)
- **SQL injection prevention** via parameterized queries
- **XSS protection** with input sanitization
- **Read-only database connections** for direct access

### Audit & Logging
- **Comprehensive access logging**
- **Progress note audit trail**
- **System event logging**
- **Performance monitoring**

## 🔄 Data Synchronization

### Direct Database Access Mode (Primary)
1. **Real-time Data** - Direct queries to MANAD Plus SQL Server
2. **No Caching Required** - Always fresh data from source
3. **Background Sync** - Periodic synchronization of incidents to local SQLite (CIMS)
4. **READ-ONLY Access** - All connections are read-only for data safety
5. **Performance** - Faster than API, no network latency

### API Mode (Backup/Fallback)
1. **Used Only When Needed** - When DB direct access is unavailable
2. **Recent Data** (last 24 hours) - Fetched from external API
3. **Older Data** (24+ hours) - Served from SQLite cache
4. **Background Sync** - Daily at 3 AM
5. **Manual Refresh** - On-demand cache updates

### Cache Management
- **Automatic expiration** after 24 hours (API mode)
- **Manual refresh** via UI buttons
- **Fallback to cache** if API fails
- **Real-time status** indicators

## 📈 Monitoring & Analytics

### Built-in Monitoring
- **Performance metrics** tracking
- **Cache hit/miss ratios**
- **API response times**
- **Database query performance**
- **User activity analytics**

### Log Analysis
- **Daily access summaries**
- **Error tracking and reporting**
- **Performance bottleneck identification**
- **Usage pattern analysis**

## 🛠️ Development & Maintenance

### Code Structure
```
ProgressReport/
├── app.py                      # Main Flask application
├── models.py                    # Database models
├── config.py                    # Configuration management
├── config_users.py             # User management
├── config_env.py               # Environment configuration
├── manad_db_connector.py       # Direct DB access
├── api_*.py                    # API integration modules
├── fcm_*.py                    # Firebase integration
├── cims_*.py                   # CIMS system modules
├── templates/                  # HTML templates
│   ├── edenfield_dashboard.html
│   ├── integrated_dashboard.html
│   ├── ProgressNoteList.html
│   └── ...
├── static/                     # CSS, JS, images
├── data/                       # Configuration files
│   └── api_keys/              # API keys and site config
├── logs/                       # Application logs
└── venv/                       # Virtual environment
```

### Key Modules
- **`manad_db_connector.py`** - **Primary**: Direct SQL Server database access (READ-ONLY)
- **`api_progressnote_fetch.py`** - Progress notes retrieval (DB primary, API backup)
- **`progress_notes_cache_manager.py`** - Caching logic (mainly for API mode)
- **`api_key_manager_json.py`** - JSON-based API key management (backup mode only)
- **`fcm_token_manager_sqlite.py`** - FCM token management
- **`cims_background_processor.py`** - Background incident synchronization
- **`cims_policy_engine.py`** - Policy-based task generation
- **`alarm_manager.py`** - Notification system

### Testing
- **Unit tests** for core functionality
- **Integration tests** for API endpoints
- **Performance benchmarks** for optimization
- **User acceptance testing** for UI/UX

## 🚀 Deployment

### Production Deployment (Windows IIS)
1. **Web Server**: IIS with FastCGI module
2. **WSGI Interface**: wfastcgi for Python integration
3. **Application Pool**: IIS-managed worker processes
4. **Database**: SQLite with regular backups
5. **Monitoring**: Built-in performance tracking

### Windows IIS Deployment Steps
```bash
# 1. Run deployment script (as Administrator)
deploy_iis.bat

# 2. Configure IIS Application Pool
# - Set .NET Framework version to "No Managed Code"
# - Set Process Model Identity to "ApplicationPoolIdentity"

# 3. Enable wfastcgi
wfastcgi-enable

# 4. Configure web.config for your environment
```

### Linux Deployment (Gunicorn)
```bash
# 1. Install Gunicorn
pip install gunicorn

# 2. Run with Gunicorn
gunicorn -c gunicorn.conf.py app:app

# 3. Use systemd for service management
# See INTERNAL_DEPLOYMENT.md for details
```

### Scaling Considerations
- **IIS Application Pool** scaling via multiple worker processes
- **Database optimization** with connection pooling
- **Static file caching** via IIS output caching
- **Load balancing** via IIS Application Request Routing (ARR)

## 📞 Support & Documentation

### Documentation Files
- **`API_USAGE.md`** - API integration guide
- **`FCM_USAGE.md`** - Firebase setup guide
- **`CIMS_README.md`** - CIMS system documentation
- **`DB_DIRECT_ACCESS_GUIDE.md`** - Direct database access setup
- **`ENV_SETUP_GUIDE.md`** - Environment configuration
- **`PERFORMANCE_DEBUGGING_GUIDE.md`** - Performance optimization
- **`SESSION_TIMEOUT_GUIDE.md`** - Session management
- **`WINDOWS_TO_INTERNAL.md`** - Windows to Linux deployment guide
- **`INTERNAL_DEPLOYMENT.md`** - Internal server deployment guide

### Troubleshooting
- **Log analysis** tools built-in
- **Performance debugging** utilities
- **Cache status** monitoring
- **Error reporting** system
- **Database connection** diagnostics

## 🎯 Future Enhancements

### Planned Features
- **Mobile app** development
- **Advanced analytics** dashboard
- **Multi-tenant** architecture
- **API rate limiting**
- **Advanced search** with Elasticsearch
- **Real-time collaboration** features

### Performance Improvements
- **Redis caching** layer
- **Database sharding** for large datasets
- **CDN integration** for global access
- **Microservices** architecture migration

---

## 📊 System Statistics

- **Total Users**: Multiple roles (Admin, Site Admin, Doctor, Physiotherapist, Operations)
- **Sites**: 5 (Parafield Gardens, Nerrilda, Ramsay, West Park, Yankalilla)
- **Database**: SQLite + SQL Server (MANAD Plus)
- **Response Time**: <10ms average
- **Uptime**: 99.9% (production)

---

## 🏢 Production Environment

### Current Deployment
- **Platform**: Windows Server with IIS (Primary) / Linux with Gunicorn (Alternative)
- **WSGI Interface**: wfastcgi (Windows) / Gunicorn (Linux)
- **Web Server**: Internet Information Services (IIS) or Nginx
- **Application Pool**: IIS-managed worker processes
- **Database**: SQLite (local) + SQL Server (MANAD Plus direct access)

### Alternative Deployments
- **Linux + Gunicorn**: For high-performance scenarios
- **Internal Linux Server**: Using provided deployment scripts
- **Docker Container**: For containerized deployments

---

## 🔑 Configuration

### Data Access Mode
The system uses **Direct Database Access as the primary method**, with API as backup only.

1. **Direct Database Access** (Primary/Default)
   - **This is the default and recommended method**
   - Set `USE_DB_DIRECT_ACCESS=true` in `system_settings` table
   - No API keys required
   - Real-time data from SQL Server
   - READ-ONLY access for safety
   - Better performance and accuracy

2. **API Mode** (Backup/Fallback Only)
   - **Use only when DB direct access is unavailable**
   - Set `USE_DB_DIRECT_ACCESS=false` in `system_settings` table
   - API keys required in `data/api_keys/api_keys.json`
   - Uses RESTful API with caching
   - Slower than direct DB access

### Site Configuration
Site database connections are configured in `data/api_keys/site_config.json`:
- Database server addresses
- Authentication method (Windows Auth or SQL Auth)
- Database names

---

*This system represents a comprehensive healthcare management platform with enterprise-grade features, supporting both direct database access and API integration for optimal flexibility and performance.*
