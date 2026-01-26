# Login Credentials

This document contains all user login credentials for the Progress Report System.

**⚠️ SECURITY WARNING**: This file contains sensitive information. Keep this document secure and do not share it publicly.

---

## System Administrators

| Username | Password | Role | Access Level |
|----------|----------|------|--------------|
| `admin` | `password123` | admin | Full system access |
| `ROD` | `rod1234!` | admin | Full system access |
| `ROD_NR` | `rodnr1234!` | admin | Full system access |
| `operation` | `password123` | admin | Operations Manager (landing: /edenfield-dashboard) |

---

## Site Administrators

| Username | Password | Role | Site Access |
|----------|----------|------|-------------|
| `PGROD` | `pgpassword` | admin | Ramsay, Nerrilda, Parafield Gardens |
| `WPROD` | `wppassword` | admin | West Park |
| `RSROD` | `rspassword` | admin | Ramsay, Nerrilda |
| `NROD` | `nrpassword` | admin | Nerrilda |
| `YKROD` | `ykpassword` | admin | Yankalilla |
| `PG_admin` | `password` | site_admin | Parafield Gardens |

---

## Doctors / General Practitioners

### All Sites Access

| Username | Password | Name | Location |
|----------|----------|------|----------|
| `ChanduraVadeen` | `Chandura123!` | Chandura Vadeen | All |
| `PaulVaska` | `Paul123!` | Paul Vaska | All |

### Parafield Gardens

| Username | Password | Name | Location |
|----------|----------|------|----------|
| `walgampola` | `1Prasanta` | Prasantha Walgampola | Parafield Gardens |

### West Park

| Username | Password | Name | Location |
|----------|----------|------|----------|
| `philipd` | `philip1234!` | Philip | West Park |

### Yankalilla

| Username | Password | Name | Location |
|----------|----------|------|----------|
| `LawJohn` | `John123!` | Siew Won (John) Law | Yankalilla |
| `LauKin` | `Kin456@` | Kin Lau | Yankalilla |
| `WorleyPaul` | `Paul789#` | Paul Worley | Yankalilla |
| `HorKC` | `KC234$` | Kok Chung (KC) Hor | Yankalilla |
| `SallehAudrey` | `Audrey567%` | Audrey Salleh | Yankalilla |
| `LiNini` | `Nini890@` | Xiaoni (Nini) Li | Yankalilla |
| `KiranantawatSoravee` | `Soravee345&` | Soravee Kiranantawat | Yankalilla |
| `BansalShiveta` | `Shiveta678*` | Shiveta Bansal | Yankalilla |
| `BehanStephen` | `Stephen901?` | Stephen Behan | Yankalilla |

---

## Summary by Role

### Admin Accounts (Full Access)
- `admin` / `password123`
- `ROD` / `rod1234!`
- `ROD_NR` / `rodnr1234!`
- `operation` / `password123`

### Site Admin Accounts
- `PGROD` / `pgpassword` (Ramsay, Nerrilda, Parafield Gardens)
- `WPROD` / `wppassword` (West Park)
- `RSROD` / `rspassword` (Ramsay, Nerrilda)
- `NROD` / `nrpassword` (Nerrilda)
- `YKROD` / `ykpassword` (Yankalilla)
- `PG_admin` / `password` (Parafield Gardens)

### Doctor Accounts
- **All Sites**: `ChanduraVadeen`, `PaulVaska`
- **Parafield Gardens**: `walgampola`
- **West Park**: `philipd`
- **Yankalilla**: `LawJohn`, `LauKin`, `WorleyPaul`, `HorKC`, `SallehAudrey`, `LiNini`, `KiranantawatSoravee`, `BansalShiveta`, `BehanStephen`

---

## Login Notes

1. **Username Case Sensitivity**: Usernames are case-insensitive (e.g., `admin`, `Admin`, `ADMIN` all work)
2. **Password Case Sensitivity**: Passwords are case-sensitive
3. **Site Selection**: Some users must select a specific site during login
4. **Session Management**: Sessions expire when the browser is closed (non-persistent)
5. **Access Control**: Users can only access sites specified in their `location` field

---

## Quick Reference

### Most Common Login Credentials

| Purpose | Username | Password |
|---------|----------|----------|
| Main Admin | `admin` | `password123` |
| ROD Admin | `ROD` | `rod1234!` |
| Parafield Gardens | `PGROD` | `pgpassword` |
| West Park | `WPROD` | `wppassword` |
| Yankalilla | `YKROD` | `ykpassword` |
| Nerrilda | `NROD` | `nrpassword` |
| Ramsay | `RSROD` | `rspassword` |

---

**Document Created**: January 2026  
**Source**: `config_users.py`  
**Total Users**: 24
