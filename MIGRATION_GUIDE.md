# Database Migration Guide

Follow this guide when running the app for the first time in a local environment or when database migration is needed.

## 🚀 Quick Start

### Windows Users

1. **Run batch file** (Simplest method)
   ```cmd
   run_migration.bat
   ```

2. Or **Run Python script directly**
   ```cmd
   python run_migration.py
   ```

### Linux/Mac Users

```bash
python3 run_migration.py
```

## 📋 What the Migration Script Does

This script automatically performs the following operations:

1. **Base Database Schema Creation**
   - Creates core tables: `users`, `fcm_tokens`, `access_logs`, etc.
   - Creates cache tables: `clients_cache`, `care_areas`, `event_types`, etc.
   - Creates configuration tables: `sites`, `sync_status`, etc.

2. **CIMS Database Schema Creation**
   - `cims_policies` - Policy management table
   - `cims_incidents` - Incident management table
   - `cims_tasks` - Task management table
   - `cims_progress_notes` - Progress notes table
   - `cims_audit_logs` - Audit log table
   - `cims_notifications` - Notifications table
   - `cims_task_assignments` - Task assignments table

3. **CIMS Incidents Table Column Additions**
   - `risk_rating` - Risk rating
   - `is_review_closed` - Review completion status
   - `is_ambulance_called` - Ambulance call status
   - `is_admitted_to_hospital` - Hospital admission status
   - `is_major_injury` - Major injury status
   - `reviewed_date` - Review date/time
   - `status_enum_id` - Status enumeration ID

4. **Database Verification**
   - Verifies all tables are created correctly
   - Checks record count for each table

## ⚠️ Important Notes

- **Existing Data Preservation**: This script preserves existing tables and data. Tables that already exist will be skipped.
- **Backup Recommended**: If you have important data, backup before migration:
  ```cmd
  copy progress_report.db progress_report.db.backup
  ```

## 🔍 Troubleshooting

### When Migration Fails

1. **Check Log File**
   ```
   migration.log
   ```
   Detailed error information is recorded in this file.

2. **Common Issues**

   **Issue**: `database_schema.sql file not found`
   - **Solution**: Run the script from the project root directory.

   **Issue**: `Permission denied` or `Access denied`
   - **Solution**: The database file may be in use by another process. Close the app and try again.

   **Issue**: `Python is not installed`
   - **Solution**: Install Python 3.11 or higher.

3. **Manual Migration**

   If the migration script fails, you can run these commands manually in order:

   ```cmd
   # 1. Create base schema
   python init_database.py

   # 2. Create CIMS tables
   python create_cims_tables.py

   # 3. Add CIMS incidents columns
   python migrate_cims_schema.py
   ```

## ✅ After Migration Completion

Once migration is completed successfully:

1. **Run Application**
   ```cmd
   python app.py
   ```

2. **Or Run Flask Development Server**
   ```cmd
   flask run
   ```

3. **Access in Browser**
   ```
   http://localhost:5000
   ```

## 📞 Need Additional Help?

- Check log file (`migration.log`)
- Refer to project README.md
- Contact development team

---

**Last Updated**: 2026-01-27
