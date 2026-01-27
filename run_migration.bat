@echo off
REM ============================================================
REM Progress Report System - Database Migration Batch Script
REM This script runs the database migration for local setup
REM ============================================================

REM Set UTF-8 encoding for proper character display
chcp 65001 >nul
echo ============================================================
echo Progress Report System - Database Migration
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed.
    echo Please install Python and try again.
    pause
    exit /b 1
)

REM Execute migration script
python run_migration.py

REM Check migration result
if errorlevel 1 (
    echo.
    echo ❌ Migration failed.
    echo Please check the migration.log file for details.
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Migration completed successfully!
    echo You can now run the application.
    pause
)
