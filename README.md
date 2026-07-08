# FYP Evaluation Management System
### UniKL MIIT — Final Year Project Conference-Style Evaluation

A Django web application for managing Final Year Project (FYP) evaluations at
Universiti Kuala Lumpur — Malaysian Institute of Information Technology (UniKL MIIT).

---

## Features by Role

### Student
- Register with course selection (only active courses shown)
- Create project groups and invite members
- Submit abstract (text/PDF) and video presentation link
- Track project registration and submission status
- View public announcements and winner rankings

### Judge
- Register for evaluation (requires PIC approval)
- View assigned projects
- Submit structured evaluation scores using PIC-managed templates
- Upload completed evaluation forms (optional)
- View evaluation status (pending/accepted/rejected)

### PIC/Admin
- **Course Management**: Add, edit, activate/deactivate courses
- **Project Management**: Approve/reject project registrations
- **Judge Management**: Approve/reject judge registrations
- **Submission Review**: Review abstract/video submissions
- **Judge Assignment**: Assign judges to approved projects
- **Evaluation Templates**: Create dynamic evaluation rubrics with criteria
- **Evaluation Review**: Review and accept/reject judge evaluations
- **Results & Rankings**: View compiled results, generate Top 3 announcements
- **CSV Export**: Export comprehensive results with all fields
- **Deadline Management**: Set registration, submission, and evaluation deadlines
- **Announcements**: Create and publish public announcements and winners

### System Features
- **Course-based separation**: Projects and results organized by course
- **Dynamic evaluation templates**: PIC creates rubrics with customizable criteria
- **Multi-judge support**: Assign multiple judges per project; scores averaged
- **Private scores**: Marks visible to PIC only; students see only rankings
- **Role-based access control**: Decorators enforce role permissions
- **In-app + email notifications**: Database notifications + console email (dev)
- **UniKL-themed UI**: Blue (#003087), gold (#C9A84C), red (#C8102E) color scheme

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

### 5. Seed demo data (optional)

```bash
python manage.py shell < evaluation/management/commands/seed_demo_data.py
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

## Demo Accounts

Use these accounts to test the system:

| Role     | Username | Password   | URL                        |
|----------|----------|------------|----------------------------|
| PIC      | pic_demo | DemoPass123! | /login/ → /pic/dashboard/ |
| Student  | student_demo | DemoPass123! | /login/ → /student/dashboard/ |
| Judge    | judge_demo | DemoPass123! | /login/ → /judge/dashboard/ |

**Note**: These accounts should be created via the registration forms or management commands. The system does not include built-in demo accounts by default.

---

## Key URLs

| URL | Description |
|-----|-------------|
| `/` | Public homepage with announcements |
| `/about/` | Evaluation process information |
| `/announcements/` | Public announcements and winners |
| `/login/` | Login for all roles |
| `/register/student/` | Student registration |
| `/register/judge/` | Judge registration |
| `/student/dashboard/` | Student dashboard |
| `/judge/dashboard/` | Judge dashboard |
| `/pic/dashboard/` | PIC dashboard |
| `/pic/courses/` | Course management (PIC) |
| `/pic/results/` | Results and Top 3 generation (PIC) |
| `/admin/` | Django admin (if superuser) |

---

## Project Structure

```
fyp_system/
├── evaluation/            # Main Django app
│   ├── models.py          # All models (User, Course, Project, Evaluation, etc.)
│   ├── forms.py           # All forms (registration, evaluation, course management)
│   ├── decorators.py      # Role-based access control decorators
│   ├── utils.py           # Notification helper, CSV export, ranking logic
│   ├── admin.py           # Django admin configuration
│   ├── urls.py            # All URL patterns
│   ├── tests.py           # Automated tests
│   ├── views/             # Views split by role
│   │   ├── auth_views.py  # Login, registration, public pages
│   │   ├── student_views.py  # Student dashboard and actions
│   │   ├── judge_views.py    # Judge dashboard and evaluation
│   │   └── pic_views.py      # PIC dashboard and management
│   ├── management/commands/
│   │   └── seed_demo_data.py  # Demo data seeding script
│   └── templates/evaluation/
│       ├── base.html       # UniKL-themed base template
│       ├── home.html      # Public homepage
│       ├── about.html     # About page
│       ├── announcements.html  # Public announcements
│       ├── auth/          # Login and registration templates
│       ├── student/       # Student page templates
│       ├── judge/         # Judge page templates
│       └── pic/           # PIC page templates
├── static/
│   ├── css/style.css      # UniKL theme (blue/gold/red)
│   └── images/            # Static images (unikl_miit_bg.jpg/webp)
├── fyp_system/            # Django project settings
├── manage.py
└── requirements.txt
```

---

## Evaluation Process

1. **Registration**: Students register accounts and create project groups
2. **Project Approval**: PIC approves/rejects project registrations
3. **Submission**: Approved projects submit abstract and video
4. **Submission Review**: PIC reviews and accepts/rejects submissions
5. **Judge Assignment**: PIC assigns judges to accepted submissions
6. **Evaluation**: Judges submit scores using active evaluation template
7. **Evaluation Review**: PIC reviews and accepts/rejects evaluations
8. **Results**: PIC generates rankings and publishes Top 3 winners

---

## Notes for Developers

- Email backend is `console` during development — emails print to terminal
- Change `SECRET_KEY` and set `DEBUG = False` for production
- Run `python manage.py collectstatic` before deploying
- SQLite is used for development; switch to PostgreSQL for production
- Run tests: `python manage.py test`
- Check for issues: `python manage.py check`
- Background image: Place `unikl_miit_bg.jpg` or `unikl_miit_bg.webp` in `static/images/`
