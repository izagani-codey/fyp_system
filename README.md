# FYP Evaluation Management System
### UniKL MIIT — Final Year Project Conference-Style Evaluation

A Django 5.2 LTS web application for managing Final Year Project (FYP) evaluations at
Universiti Kuala Lumpur — Malaysian Institute of Information Technology (UniKL MIIT).

---

## Features

- **Three roles**: Student, Judge, PIC/Admin
- **Project/Group-based evaluation**: One or more students per project
- **Multi-judge support**: Assign multiple judges per project
- **Deadline enforcement**: Registration, submission, and evaluation deadlines
- **Conference-style evaluation form**: 6 criteria totalling 95 marks
- **Private scores**: Marks visible to PIC only; students see only Evaluated/Pending
- **CSV export**: Download all results as a CSV file
- **Public announcements**: PIC publishes winners and announcements
- **In-app + email notifications**: Database notifications + Django console email (dev)

---

## Quick Start — Pop!_OS Linux + VS Code

### Prerequisites
- Python 3.12+
- VS Code with extensions: Python, Django, SQLite Viewer

### 1. Clone / navigate to the project

```bash
cd /home/<your-username>/Projects/fyp_system
```

### 2. Create and activate the virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Apply database migrations

```bash
python manage.py migrate
```

### 5. Create a PIC/Admin account

**Option A — Superuser (has Django admin access)**
```bash
python manage.py createsuperuser
# Then assign PIC role:
python manage.py shell -c "
from django.contrib.auth.models import User
from evaluation.models import UserProfile
u = User.objects.get(username='YOUR_USERNAME')
UserProfile.objects.get_or_create(u, defaults={'role': 'pic'})
"
```

**Option B — PIC user via management command (recommended)**
```bash
python manage.py create_pic --username pic_admin --email pic@unikl.edu.my --password Admin@1234
```

### 6. Start the development server

```bash
python manage.py runserver
```

Open: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### 7. VS Code Setup

Open the project folder in VS Code:
```bash
code /home/<your-username>/Projects/fyp_system
```

Select the Python interpreter: `Ctrl+Shift+P` → **Python: Select Interpreter** → choose `./venv/bin/python`

---

## Default Test Accounts (created during setup above)

| Role     | Username | Password   | URL            |
|----------|----------|------------|----------------|
| Admin/PIC (superuser) | admin | Admin@1234 | /admin/ |
| PIC      | pic1     | PIC@1234   | /login/ → /pic/dashboard/ |

---

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Public homepage |
| `/about/` | Evaluation process info |
| `/announcements/` | Public announcements/winners |
| `/login/` | Login for all roles |
| `/register/student/` | Student registration |
| `/register/judge/` | Judge registration |
| `/student/dashboard/` | Student dashboard |
| `/judge/dashboard/` | Judge dashboard |
| `/pic/dashboard/` | PIC dashboard |
| `/admin/` | Django admin |

---

## GitHub Setup

```bash
cd /home/<your-username>/Projects/fyp_system
git init   # already done
git remote add origin https://github.com/YOUR_USERNAME/fyp-evaluation-system.git
git push -u origin master
```

---

## Project Structure

```
fyp_system/
├── evaluation/            # Main Django app
│   ├── models.py          # All 11 models
│   ├── forms.py           # All 8 forms
│   ├── decorators.py      # Role + deadline decorators
│   ├── utils.py           # Notification helper + CSV export
│   ├── admin.py           # Django admin config
│   ├── urls.py            # All URL patterns
│   ├── views/             # Views split by role
│   │   ├── auth_views.py
│   │   ├── student_views.py
│   │   ├── judge_views.py
│   │   └── pic_views.py
│   ├── management/commands/
│   │   └── create_pic.py  # python manage.py create_pic
│   └── templates/evaluation/
│       ├── base.html       # UniKL-themed base
│       ├── home.html
│       ├── about.html
│       ├── announcements.html
│       ├── auth/           # login, register templates
│       ├── student/        # student page templates
│       ├── judge/          # judge page templates
│       └── pic/            # PIC page templates
├── static/css/style.css    # UniKL theme (blue/gold/red)
├── fyp_system/             # Django project settings
├── manage.py
└── requirements.txt
```

---

## Notes for Developers

- Email backend is `console` during development — emails print to terminal
- Change `SECRET_KEY` and set `DEBUG = False` for production
- Run `python manage.py collectstatic` before deploying
- SQLite is used for development; switch to PostgreSQL for production
