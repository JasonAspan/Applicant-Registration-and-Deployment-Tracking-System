# Applicant Tracking System (ATS)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-blue)](https://flask.palletsprojects.com/) [![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-green)](https://www.postgresql.org/)

## Overview
A full-stack Flask web application for applicant CV submissions and employee management dashboard. Supports PDF CV uploads, employee auth/profile pics, searchable dashboard with batch export/delete.

**Key Features**:
- Applicant: Form + PDF CV upload (validated).
- Employee: Register/Login, Profile pic, Dashboard (search/filter/sort by name/position/date, download CVs, batch ZIP export/delete).
- Secure file handling, SQLAlchemy ORM, Flask-Login.
- Dual-mode: Applicant/Employee servers or combined.

## Hardware Requirements

### Development
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | Dual-core 2GHz | Quad-core 3GHz+ |
| RAM | 8GB | 16GB |
| Storage | 10GB SSD | 50GB SSD |
| OS | Windows 10/11, macOS, Linux | Same |
| Network | Stable internet (Docker pulls) | Same |

### Production
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 1 vCPU | 2 vCPU+ |
| RAM | 2GB | 4GB+ |
| Storage | 20GB SSD (DB growth) | 100GB+ |
| Server | VPS (DigitalOcean/Linode $10/mo) | Cloud (AWS EC2 t3.micro) |
| DB | Managed PostgreSQL (free tier) | Dedicated instance |

## Development Process
1. **Setup Environment**:
   ```
   # Clone (if git repo)
   git clone <repo> & cd "Applicant Tracking System"

   # Virtual env (Python 3.10+)
   python -m venv ats_env
   ats_env\Scripts\activate  # Windows

   # Install deps
   pip install -r requirements.txt
   ```

2. **Database Setup**:
   - Local SQLite (default fallback).
   - Or PostgreSQL via Docker:
     ```
     docker-compose up -d db
     ```

3. **Create .env** (optional, overrides config.py):
   ```
   SECRET_KEY=your-secure-key-change-in-prod
   DATABASE_URL=postgresql://postgres:pass@localhost:5432/ats
   ```

4. **Run & Test**:
   ```
   # Combined app
   python app.py  # http://127.0.0.1:5000

   # Or separate
   python applicant_server.py  # 5001
   python employee_server.py   # 5002
   ```

5. **Coding Workflow**:
   - Edit models/routes/templates.
   - Auto-migrate: `ensure_db_schema()` in ats_app.py.
   - Test flows: Applicant submit → Employee dashboard view/download.

6. **Testing**:
   - Manual: Register/login, upload CV/profile pic, filter/export.
   - Check logs: `applicant_server.log`, `employee_server.log`.
   - Fix issues (see Troubleshooting).

7. **Current TODO** (from TODO.md):
   - Dashboard safeguards, script src fixes.
   - Run `taskkill /f /im python.exe` before restarts.

## Deployment Process
1. **Local Prod-like**:
   ```
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. **Docker Fullstack**:
   - Extend docker-compose.yml with Flask service.
   ```
   services:
     app:
       build: .
       ports: [\"5000:5000\"]
       depends_on: [db]
   ```

3. **Cloud VPS**:
   ```
   # Ubuntu VPS
   sudo apt update && sudo apt install python3-pip docker.io docker-compose nginx
   git pull
   pip install -r requirements.txt
   sudo ufw allow 80,443,5000
   # PM2/Gunicorn + Nginx reverse proxy
   # Certbot SSL
   ```

4. **Heroku** (quick):
   ```
   # Procfile: web: gunicorn app:app
   heroku create ats-app
   heroku addons:create heroku-postgresql:hobby-dev
   git push heroku main
   ```

## Architecture
```
Applicant Form --> CV Upload --> DB (PostgreSQL/SQLite)
                      |
                 Employee Dashboard (Search/Filter/Batch Ops)
```
- **Frontend**: Jinja2 + Bootstrap-ish CSS/JS.
- **Backend**: Flask Blueprints.
- **Data**: SQLAlchemy, file blobs in DB.

## Quick Start
```
pip install -r requirements.txt
python run.py
```
- Applicant: `/applicant-register.html`
- Employee: `/employee-register.html` → `/dashboard.html`

## Configuration
See `config.py`, override with `.env`.

## Database Schema
- **Employee**: id, username, email, password_hash, profile_*(filename/data).
- **Applicant**: full details, cv_*(filename/data), status='pending', employee_id FK.

## Usage Guides
### Applicant
1. Fill form, upload PDF CV.
2. Submit → Success flash.

### Employee
1. Register/Login.
2. `/dashboard.html`: Search `q`, filter position/date, sort.
3. Select → Download CV or Batch ZIP/Delete.

## API Routes Summary
| Method | Path | Auth | Desc |
|--------|------|------|------|
| POST | /applicant-register.html | - | Submit app |
| GET/POST | /employee-login.html | - | Login |
| GET | /dashboard.html | Yes | List |
| POST | /applicants/batch-export-cv | Yes | ZIP CVs |
| GET | /applicants/<id>/cv | Yes | Single CV |

## Troubleshooting
- **ERR_CONNECTION_REFUSED**: Start server `python app.py`.
- **DB Errors**: `docker-compose up -d db` or check DATABASE_URL.
- **Upload Fails**: PDF only, <2MB pics.
- Logs: `*_server.log`.

## Next Steps
See [TODO.md](TODO.md) for ongoing fixes.

## License
MIT (add your own).

