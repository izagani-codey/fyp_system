"""
Management command: seed_demo_data
===================================
Populates the FYP Evaluation Management System with realistic demo data
for testing the full conference-style workflow.

Usage:
    python manage.py seed_demo_data

IDEMPOTENT — safe to run multiple times. All seeded records use
deterministic identifiers so get_or_create finds them on re-runs.
Random choices are fixed via random.seed(42).
"""

import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from evaluation.models import (
    Announcement,
    Course,
    Deadline,
    EvaluationCriterion,
    EvaluationScore,
    EvaluationSubmission,
    EvaluationTemplate,
    JudgeAssignment,
    JudgeProfile,
    Notification,
    Project,
    ProjectMember,
    ProjectSubmission,
    StudentProfile,
    UserProfile,
)

# Fix the random seed so every run produces identical data.
# get_or_create then finds existing records rather than creating duplicates.
random.seed(42)

# ── Static data pools ─────────────────────────────────────────────────────────

PROGRAMMES = [
    "Diploma in Information Technology",
    "Bachelor of Information Technology",
    "Bachelor of Computer Engineering Technology",
    "Diploma in Multimedia",
]

SECTIONS = ["DIT6A", "DIT6B", "BIT7A", "BIT7B", "DMM5A"]

SUPERVISORS = [
    "Dr. Mohd Azri Bin Zakaria",
    "Ms. Nurul Hidayah Binti Salleh",
    "Mr. Hafizuddin Bin Ramli",
    "Dr. Siti Aisyah Binti Omar",
    "Mr. Khairul Nizam Bin Hassan",
    "Dr. Faridah Binti Yusof",
    "Ms. Rozita Binti Ibrahim",
    "Mr. Syafiq Bin Abdullah",
]

# 29 student full names (deterministic order)
STUDENT_NAMES = [
    "Ahmad Fadzli Bin Razali",
    "Nurul Aina Binti Hassan",
    "Muhammad Haziq Bin Ibrahim",
    "Siti Fatimah Binti Yusof",
    "Farhan Syahril Bin Othman",
    "Amirah Binti Kamaruddin",
    "Luqman Hakim Bin Zainal",
    "Nadia Binti Wahab",
    "Danish Irfan Bin Alias",
    "Zulaikha Binti Ghazali",
    "Azri Hafiz Bin Mansor",
    "Syahira Binti Abdullah",
    "Nabil Akmal Bin Hamid",
    "Intan Binti Mohd Noor",
    "Izzat Radzif Bin Saad",
    "Farhana Binti Ismail",
    "Khairul Syafiq Bin Jaafar",
    "Hana Binti Rahman",
    "Muhammad Aiman Bin Yahya",
    "Nabila Binti Sulaiman",
    "Zulhilmi Bin Wahid",
    "Liyana Binti Aziz",
    "Hafiz Irfan Bin Radzi",
    "Umairah Binti Dzulkifli",
    "Syafiq Hakim Bin Nordin",
    "Raihan Binti Ruslan",
    "Rizwan Nabil Bin Hashim",
    "Adlina Binti Zakaria",
    "Izzah Diyana Binti Nawi",
]

# 5 judge definitions (name, department, expertise)
JUDGE_DEFS = [
    (
        "Dr. Rashidah Binti Mokhtar",
        "Computer Science",
        "Artificial Intelligence, Machine Learning",
    ),
    (
        "Mr. Zulkifli Bin Hamdan",
        "Software Engineering",
        "Mobile Development, Software Testing",
    ),
    (
        "Dr. Norazlina Binti Kadir",
        "Information Systems",
        "Database Systems, Data Analytics",
    ),
    ("Mr. Hafiz Bin Sulaiman", "Networking", "Cybersecurity, Cloud Computing"),
    ("Ms. Erna Binti Mohd Rashid", "Multimedia", "UI/UX Design, Frontend Development"),
]

# 11 project definitions (title, programme, section, supervisor index, status)
# status distribution: 8 approved, 2 pending, 1 rejected  (~70/20/10%)
PROJECT_DEFS = [
    ("Campus Lost and Found System", 0, 0, 0, "approved"),
    ("Online Appointment Booking System", 1, 2, 1, "approved"),
    ("Smart Attendance Monitoring System", 0, 1, 2, "approved"),
    ("E-Learning Progress Tracker", 1, 3, 3, "approved"),
    ("Inventory Management System for Small Businesses", 2, 4, 4, "approved"),
    ("Student Complaint Management System", 0, 0, 5, "approved"),
    ("Event Registration and QR Check-In System", 1, 1, 6, "approved"),
    ("Library Seat Booking System", 3, 2, 7, "approved"),
    ("Food Ordering System for Campus Cafeteria", 0, 3, 0, "pending"),
    ("Internship Application Tracking System", 1, 4, 1, "pending"),
    ("Maintenance Request Management System", 2, 0, 2, "rejected"),
]

ABSTRACTS = [
    (
        "This system aims to automate and streamline the management process, "
        "reducing manual effort and improving accuracy. Key features include "
        "user authentication, data management, and reporting modules."
    ),
    (
        "The proposed system provides a digital solution to an existing manual process. "
        "It enables real-time tracking, notifications, and an admin dashboard for "
        "comprehensive oversight of all operational activities."
    ),
    (
        "Built using modern web technologies, this system offers a mobile-responsive "
        "interface, secure login, and intuitive navigation. It solves a common problem "
        "faced by students and staff in the campus environment."
    ),
    (
        "This project introduces a smart, integrated platform that replaces paper-based "
        "workflows with a fully digital experience. The system supports multiple user roles "
        "and includes real-time data synchronisation and comprehensive audit trails."
    ),
]

VIDEO_LINKS = [
    "https://youtu.be/demo-project-alpha",
    "https://drive.google.com/file/d/demo-beta-2026",
    "https://youtu.be/demo-project-gamma",
    "https://drive.google.com/file/d/demo-delta-2026",
    "https://youtu.be/demo-project-epsilon",
]

EVAL_COMMENTS = [
    "Good work overall. The system demonstrates a solid understanding of the problem domain.",
    "The abstract clearly explains the project scope. Implementation could be further improved.",
    "Impressive functionality demonstrated. The video presentation was clear and concise.",
    "Strong technical implementation. Innovation aspects could be highlighted more prominently.",
    "Well-structured project. The problem statement is clearly defined and addressed.",
    "Good effort. The system works as intended but could benefit from more thorough testing.",
    "Creative solution to a real-world problem. The UI/UX design is commendable.",
    "The presentation was engaging. Technical depth needs improvement in certain areas.",
    "Solid project with good documentation. Minor improvements recommended for the abstract.",
    "Excellent innovation. The system has clear potential for real-world deployment.",
]

NOTIF_MESSAGES = [
    "Your student account has been registered. Welcome to the FYP Evaluation System.",
    "Your project registration is pending PIC approval.",
    "Your project has been approved! You can now submit your abstract and video.",
    "Your project registration was rejected. Please contact PIC for more information.",
    "Your submission has been received and is under review by the PIC.",
    "Your submission has been accepted! Judges will be assigned soon.",
    "Your submission was rejected. Please review PIC remarks and resubmit.",
    "You have been assigned to evaluate a new project. Log in to view details.",
    "Your project has been evaluated by an assigned judge.",
    "A new announcement has been published. Check the announcements page.",
    "Reminder: The submission deadline is approaching. Please submit your materials.",
    "Your judge registration is pending PIC approval.",
    "Your judge registration has been approved! You can now access assigned projects.",
]


def _make_phone(seed_val):
    """Generate a deterministic-looking Malaysian phone number."""
    prefixes = ["011", "012", "013", "014", "016", "017", "018", "019"]
    prefix = prefixes[seed_val % len(prefixes)]
    rest = str(1000000 + (seed_val * 7919 % 9000000)).zfill(7)
    return prefix + rest


class Command(BaseCommand):
    help = "Seed realistic demo data for the FYP Evaluation Management System"

    def handle(self, *args, **options):
        # Re-seed random on every call so values are deterministic even if the
        # module-level seed ran at import time with other state.
        random.seed(42)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "\n=== FYP Evaluation System — Seeding Demo Data ===\n"
            )
        )

        # ── Step 1: Known PIC account ────────────────────────────────────────
        self.stdout.write("  [1/17] Known PIC account (pic_demo)...")
        pic_user, _ = User.objects.get_or_create(
            username="pic_demo",
            defaults={
                "email": "pic.demo@unikl.edu.my",
                "first_name": "Dr. Aina",
                "last_name": "Rahman",
                "is_staff": True,
                "is_superuser": False,
            },
        )
        pic_user.set_password("DemoPass123!")
        pic_user.save()
        UserProfile.objects.get_or_create(user=pic_user, defaults={"role": "pic"})

        # ── Step 2: Second PIC account ───────────────────────────────────────
        self.stdout.write("  [2/17] Second PIC account (pic_coordinator)...")
        pic2_user, _ = User.objects.get_or_create(
            username="pic_coordinator",
            defaults={
                "email": "pic.coordinator@unikl.edu.my",
                "first_name": "En. Zaidi",
                "last_name": "Mohd Arif",
                "is_staff": True,
                "is_superuser": False,
            },
        )
        pic2_user.set_password("PIC@coord2026")
        pic2_user.save()
        UserProfile.objects.get_or_create(user=pic2_user, defaults={"role": "pic"})

        # ── Step 3: Known Student account ───────────────────────────────────
        self.stdout.write("  [3/17] Known Student account (student_demo)...")
        student_demo_user, _ = User.objects.get_or_create(
            username="student_demo",
            defaults={
                "email": "student.demo@unikl.edu.my",
                "first_name": "Adam",
                "last_name": "Hakimi",
            },
        )
        student_demo_user.set_password("DemoPass123!")
        student_demo_user.save()
        UserProfile.objects.get_or_create(
            user=student_demo_user, defaults={"role": "student"}
        )
        student_demo_profile, _ = StudentProfile.objects.get_or_create(
            student_id="52211223344",
            defaults={
                "user": student_demo_user,
                "full_name": "Adam Hakimi",
                "programme": "Diploma in Information Technology",
                "section": "DIT6A",
                "phone_number": "0123456789",
            },
        )

        # ── Step 4: Known Judge account ──────────────────────────────────────
        self.stdout.write("  [4/17] Known Judge account (judge_demo)...")
        judge_demo_user, _ = User.objects.get_or_create(
            username="judge_demo",
            defaults={
                "email": "judge.demo@unikl.edu.my",
                "first_name": "Mr. Farhan",
                "last_name": "Iskandar",
            },
        )
        judge_demo_user.set_password("DemoPass123!")
        judge_demo_user.save()
        UserProfile.objects.get_or_create(
            user=judge_demo_user, defaults={"role": "judge"}
        )
        judge_demo_profile, _ = JudgeProfile.objects.get_or_create(
            user=judge_demo_user,
            defaults={
                "full_name": "Mr. Farhan Iskandar",
                "department": "Software Engineering",
                "expertise_area": "Web Development, Django, System Evaluation",
                "phone_number": "0198765432",
                "registration_status": "approved",
            },
        )
        if judge_demo_profile.registration_status != "approved":
            judge_demo_profile.registration_status = "approved"
            judge_demo_profile.save()

        # ── Course and default rubric support ────────────────────────────────
        courses = {}
        for course_name, course_code in [
            ("Computer Science", "CS"),
            ("Artificial Intelligence", "AI"),
            ("Cyber Security", "CYB"),
            ("Software Engineering", "SE"),
            ("Information Technology", "IT"),
            ("Multimedia", "MM"),
            ("Networking", "NET"),
        ]:
            course, _ = Course.objects.get_or_create(
                code=course_code,
                defaults={
                    "name": course_name,
                    "description": f"{course_name} FYP course.",
                    "is_active": True,
                },
            )
            courses[course_code] = course

        active_template = EvaluationTemplate.objects.filter(is_active=True).first()
        if not active_template:
            active_template = EvaluationTemplate.objects.create(
                title="Default FYP Evaluation Template",
                description="Default 95-mark dynamic rubric.",
                is_active=True,
                created_by=pic_user,
            )
        if not active_template.criteria.exists():
            for name, max_score, order in [
                ("Abstract Quality", 10, 1),
                ("Problem Statement", 15, 2),
                ("System Functionality", 25, 3),
                ("Technical Implementation", 20, 4),
                ("Presentation / Video Quality", 15, 5),
                ("Innovation and Value", 10, 6),
            ]:
                EvaluationCriterion.objects.create(
                    template=active_template,
                    name=name,
                    max_score=max_score,
                    order=order,
                )
        criteria = list(active_template.criteria.all())
        if not student_demo_profile.course_id:
            student_demo_profile.course = courses["IT"]
            student_demo_profile.save(update_fields=["course"])

        # ── Step 5: Known Project ────────────────────────────────────────────
        self.stdout.write(
            "  [5/17] Known project (Smart Clinic Queue Management System)..."
        )
        known_project, _ = Project.objects.get_or_create(
            title="Smart Clinic Queue Management System",
            leader=student_demo_profile,
            defaults={
                "programme": "Diploma in Information Technology",
                "course": courses["IT"],
                "section": "DIT6A",
                "supervisor_name": "Ms. Nurul Hidayah",
                "registration_status": "approved",
                "pic_remarks": "Well-defined scope and clear objectives. Approved.",
            },
        )
        if not known_project.course_id:
            known_project.course = courses["IT"]
            known_project.save(update_fields=["course"])

        # ── Step 6: Known Submission ─────────────────────────────────────────
        self.stdout.write("  [6/17] Known submission (accepted)...")
        known_submission, _ = ProjectSubmission.objects.get_or_create(
            project=known_project,
            defaults={
                "abstract_text": (
                    "This project proposes a Smart Clinic Queue Management System designed to "
                    "reduce waiting time, improve patient flow, and assist clinic staff in managing "
                    "daily appointments and walk-in patients. The system includes patient registration, "
                    "queue tracking, staff dashboard, and reporting features."
                ),
                "video_link": "https://youtu.be/dummy-fyp-demo",
                "status": "accepted",
                "submitted_at": timezone.now() - timedelta(days=10),
                "reviewed_at": timezone.now() - timedelta(days=7),
                "pic_remarks": "Clear abstract and good video presentation. Accepted.",
            },
        )
        if known_submission.status != "accepted":
            known_submission.status = "accepted"
            known_submission.submitted_at = timezone.now() - timedelta(days=10)
            known_submission.reviewed_at = timezone.now() - timedelta(days=7)
            known_submission.save()

        # ── Step 7: Known Assignment (no evaluation) ─────────────────────────
        self.stdout.write(
            "  [7/17] Known judge assignment (no evaluation — manual test)..."
        )
        known_assignment, _ = JudgeAssignment.objects.get_or_create(
            judge=judge_demo_profile,
            project=known_project,
        )
        # Explicitly do NOT create an Evaluation for this assignment.

        # ── Step 8: 29 random student users ─────────────────────────────────
        self.stdout.write("  [8/17] 29 random student users (seed_student_01 … 29)...")
        random_students = []
        for i, full_name in enumerate(STUDENT_NAMES, start=1):
            username = f"seed_student_{i:02d}"
            student_id = f"SEED{i:06d}"
            u, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@student.unikl.edu.my"},
            )
            u.set_password("Student@2026")
            u.save()
            UserProfile.objects.get_or_create(user=u, defaults={"role": "student"})
            course_choices = [
                courses["IT"],
                courses["CS"],
                courses["SE"],
                courses["MM"],
                courses["NET"],
                courses["AI"],
                courses["CYB"],
            ]
            sp, _ = StudentProfile.objects.get_or_create(
                student_id=student_id,
                defaults={
                    "user": u,
                    "full_name": full_name,
                    "programme": PROGRAMMES[i % len(PROGRAMMES)],
                    "course": course_choices[i % len(course_choices)],
                    "section": SECTIONS[i % len(SECTIONS)],
                    "phone_number": _make_phone(i),
                },
            )
            if not sp.course_id:
                sp.course = course_choices[i % len(course_choices)]
                sp.save(update_fields=["course"])
            random_students.append(sp)

        # ── Step 9: 5 random judge users ─────────────────────────────────────
        self.stdout.write("  [9/17] 5 random judge users (seed_judge_01 … 05)...")
        random_judges = []
        for i, (jname, dept, expertise) in enumerate(JUDGE_DEFS, start=1):
            username = f"seed_judge_{i:02d}"
            j_user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@unikl.edu.my"},
            )
            j_user.set_password("Judge@2026")
            j_user.save()
            UserProfile.objects.get_or_create(user=j_user, defaults={"role": "judge"})
            jp, _ = JudgeProfile.objects.get_or_create(
                user=j_user,
                defaults={
                    "full_name": jname,
                    "department": dept,
                    "expertise_area": expertise,
                    "phone_number": _make_phone(100 + i),
                    "registration_status": "approved",
                },
            )
            if jp.registration_status != "approved":
                jp.registration_status = "approved"
                jp.save()
            random_judges.append(jp)

        all_judges = [judge_demo_profile] + random_judges  # 6 total

        # ── Step 10: 11 random projects ──────────────────────────────────────
        # Deterministic: PROJECT_DEFS specifies title, programme/section indices,
        # supervisor index, and status for each project.
        self.stdout.write("  [10/17] 11 random projects...")

        # Assign leaders from random_students in fixed order (students 0–10)
        project_leaders = random_students[:11]
        random_projects = []

        for idx, (title, prog_idx, sec_idx, sup_idx, status) in enumerate(PROJECT_DEFS):
            leader = project_leaders[idx]
            remarks = ""
            if status == "approved":
                remarks = "Project meets all requirements. Approved for evaluation."
            elif status == "rejected":
                remarks = "Incomplete project description. Please revise and resubmit."

            proj, _ = Project.objects.get_or_create(
                title=title,
                leader=leader,
                defaults={
                    "programme": PROGRAMMES[prog_idx],
                    "course": leader.course,
                    "section": SECTIONS[sec_idx],
                    "supervisor_name": SUPERVISORS[sup_idx],
                    "registration_status": status,
                    "pic_remarks": remarks,
                },
            )
            if not proj.course_id:
                proj.course = leader.course
                proj.save(update_fields=["course"])
            random_projects.append(proj)

        all_projects = [known_project] + random_projects  # 12 total
        approved_projects = [
            p for p in all_projects if p.registration_status == "approved"
        ]

        # ── Step 11: Group members ────────────────────────────────────────────
        self.stdout.write("  [11/17] Adding group members to 5 projects...")
        # Use students 11–22 as members, fixed pairs, idempotent via get_or_create
        member_students = random_students[11:23]
        member_assignments = [
            (random_projects[0], member_students[0]),
            (random_projects[0], member_students[1]),
            (random_projects[1], member_students[2]),
            (random_projects[2], member_students[3]),
            (random_projects[2], member_students[4]),
            (random_projects[3], member_students[5]),
            (random_projects[4], member_students[6]),
            (random_projects[4], member_students[7]),
            (random_projects[5], member_students[8]),
            (random_projects[6], member_students[9]),
        ]
        for proj, student in member_assignments:
            ProjectMember.objects.get_or_create(project=proj, student=student)

        # ── Step 12: Submissions for approved projects ────────────────────────
        # Distribution: 60% accepted, 25% pending_review, 15% rejected
        # Known project's submission is already accepted.
        # The 8 other approved projects get:
        #   accepted: projects 0,1,2,3,4  (5 of 8 other = 63%)
        #   pending_review: projects 5,6   (2 of 8 = 25%)
        #   rejected: project 7            (1 of 8 = 12%)
        self.stdout.write("  [12/17] Submissions for approved projects...")

        other_approved = [p for p in approved_projects if p.id != known_project.id]
        sub_statuses = (
            ["accepted"] * 5
            + ["pending_review"] * 2
            + ["rejected"] * max(0, len(other_approved) - 7)
        )
        # Pad to length if needed
        while len(sub_statuses) < len(other_approved):
            sub_statuses.append("accepted")
        sub_statuses = sub_statuses[: len(other_approved)]

        for proj, sub_status in zip(other_approved, sub_statuses):
            reviewed_at = None
            sub_remarks = ""
            if sub_status == "accepted":
                sub_remarks = "Abstract and video reviewed. Submission accepted."
                reviewed_at = timezone.now() - timedelta(days=random.randint(3, 15))
            elif sub_status == "rejected":
                sub_remarks = "Abstract lacks sufficient detail. Video link not accessible. Please resubmit."
                reviewed_at = timezone.now() - timedelta(days=random.randint(1, 8))

            ProjectSubmission.objects.get_or_create(
                project=proj,
                defaults={
                    "abstract_text": random.choice(ABSTRACTS),
                    "video_link": random.choice(VIDEO_LINKS),
                    "status": sub_status,
                    "submitted_at": timezone.now()
                    - timedelta(days=random.randint(12, 35)),
                    "reviewed_at": reviewed_at,
                    "pic_remarks": sub_remarks,
                },
            )

        # Ensure every approved project has a submission record
        for proj in approved_projects:
            ProjectSubmission.objects.get_or_create(
                project=proj,
                defaults={"status": "not_submitted"},
            )

        # ── Step 13: 14 random judge assignments ──────────────────────────────
        # Fixed assignment pairs (deterministic) so re-runs are idempotent.
        # 15 total including the known assignment. 10 will get evaluations; 5 pending.
        self.stdout.write("  [13/17] 14 random judge assignments...")

        # Accepted projects available for assignment (excluding known_project)
        accepted_projs = [
            p
            for p in all_projects
            if p.id != known_project.id and p.registration_status == "approved"
        ]

        # Fixed assignment table: (judge index in random_judges, project index in accepted_projs)
        # 14 pairs, all unique (judge, project) combinations
        assignment_table = [
            (0, 0),
            (0, 1),
            (0, 2),
            (1, 2),
            (1, 3),
            (1, 4),
            (2, 0),
            (2, 3),
            (2, 5),
            (3, 1),
            (3, 4),
            (3, 6),
            (4, 5),
            (4, 6),
        ]

        random_assignments = []
        for judge_idx, proj_idx in assignment_table:
            if judge_idx >= len(random_judges):
                continue
            if proj_idx >= len(accepted_projs):
                continue
            judge = random_judges[judge_idx]
            proj = accepted_projs[proj_idx]
            asst, _ = JudgeAssignment.objects.get_or_create(judge=judge, project=proj)
            random_assignments.append(asst)

        # ── Step 14: 10 evaluation form submissions ───────────────────────────
        # First 10 of random_assignments have submitted forms:
        #   8 accepted, 1 pending_review, 1 rejected
        # Last 4 assignments remain unsubmitted (for manual testing).
        self.stdout.write(
            "  [14/17] 10 evaluation form submissions (8 accepted, 1 pending, 1 rejected)..."
        )

        sub_statuses_14 = ["accepted"] * 8 + ["pending_review"] + ["rejected"]
        sub_remarks_14 = [
            "Evaluation form completed as per the rubric provided.",
            "Scores given based on video presentation and abstract review.",
            "Completed evaluation form attached.",
            "All criteria assessed. See attached form for detailed scores.",
            "Evaluation completed after reviewing all submitted materials.",
            "Form completed. Minor deductions noted for presentation quality.",
            "Abstract quality and innovation sections evaluated thoroughly.",
            "Completed form uploaded. Strong project overall.",
            "Pending — form uploaded, awaiting PIC review.",
            "Initial submission. Will revise based on feedback.",  # rejected
        ]
        pic_feedback_14 = (
            [""] * 8
            + [""]
            + [
                "Please recheck the scoring on System Functionality — values appear inconsistent with the project scope."
            ]
        )

        now = timezone.now()
        for i, (asst, status, remarks, feedback) in enumerate(
            zip(
                random_assignments[:10],
                sub_statuses_14,
                sub_remarks_14,
                pic_feedback_14,
            )
        ):
            reviewed_at = None
            reviewed_by = None
            if status in ("accepted", "rejected"):
                reviewed_at = now - timedelta(days=random.randint(1, 7))
                reviewed_by = pic_user

            eval_submission, _ = EvaluationSubmission.objects.get_or_create(
                assignment=asst,
                defaults={
                    "template": active_template,
                    "completed_form_file": f"evaluation_forms/seed_eval_form_{i + 1:02d}.pdf",
                    "remarks": remarks,
                    "status": status,
                    "submitted_at": now - timedelta(days=random.randint(8, 20)),
                    "reviewed_by": reviewed_by,
                    "reviewed_at": reviewed_at,
                    "pic_feedback": feedback,
                },
            )
            if not eval_submission.template_id:
                eval_submission.template = active_template
                eval_submission.save(update_fields=["template"])
            if criteria and not eval_submission.scores.exists():
                for criterion in criteria:
                    score = max(0, criterion.max_score - random.randint(0, 4))
                    EvaluationScore.objects.create(
                        submission=eval_submission,
                        criterion=criterion,
                        score=score,
                    )
                eval_submission.recalculate_total()

        # ── Step 15: Deadlines ────────────────────────────────────────────────
        self.stdout.write("  [15/17] Active deadlines (14 / 30 / 45 days from now)...")
        now = timezone.now()
        Deadline.objects.update_or_create(
            deadline_type="registration",
            defaults={"deadline_date": now + timedelta(days=14), "is_active": True},
        )
        Deadline.objects.update_or_create(
            deadline_type="submission",
            defaults={"deadline_date": now + timedelta(days=30), "is_active": True},
        )
        Deadline.objects.update_or_create(
            deadline_type="evaluation",
            defaults={"deadline_date": now + timedelta(days=45), "is_active": True},
        )

        # ── Step 16: Announcements ────────────────────────────────────────────
        self.stdout.write("  [16/17] 3 public announcements...")
        now = timezone.now()
        ann_data = [
            {
                "title": "FYP Evaluation Registration is Open",
                "content": (
                    "Dear Students and Judges,\n\n"
                    "The FYP Evaluation System for the current semester is now open for registration. "
                    "Students are required to register their project groups and submit project details "
                    "before the registration deadline.\n\n"
                    "Judges are also invited to register and await approval from the PIC.\n\n"
                    "Please log in to the system to begin.\n\n"
                    "Thank you.\n\nUniKL MIIT FYP Evaluation Committee"
                ),
                "is_winners": False,
                "is_published": True,
                "published_at": now - timedelta(days=20),
            },
            {
                "title": "Abstract and Video Submission Deadline Reminder",
                "content": (
                    "Dear Project Leaders,\n\n"
                    "This is a reminder that the abstract and video submission deadline is approaching. "
                    "All approved project leaders must submit their abstract and video presentation "
                    "link before the deadline shown on your student dashboard.\n\n"
                    "Late submissions will not be accepted.\n\n"
                    "Thank you.\n\nUniKL MIIT FYP Evaluation Committee"
                ),
                "is_winners": False,
                "is_published": True,
                "published_at": now - timedelta(days=10),
            },
            {
                "title": "Final Evaluation Results Will Be Announced Soon",
                "content": (
                    "Dear All,\n\n"
                    "The evaluation process is nearing completion. The PIC will compile all "
                    "evaluation scores and announce final results and winners upon completion "
                    "of all scheduled evaluations.\n\n"
                    "Students are reminded that individual evaluation marks are confidential. "
                    "Only winners and general results will be published publicly.\n\n"
                    "Stay tuned!\n\nUniKL MIIT FYP Evaluation Committee"
                ),
                "is_winners": False,
                "is_published": True,
                "published_at": now - timedelta(days=2),
            },
        ]
        for ann in ann_data:
            Announcement.objects.get_or_create(
                title=ann["title"],
                defaults={
                    "content": ann["content"],
                    "is_winners": ann["is_winners"],
                    "is_published": ann["is_published"],
                    "published_at": ann["published_at"],
                    "created_by": pic_user,
                },
            )

        # ── Step 17: Notifications ────────────────────────────────────────────
        # Only bulk-create if total count < 80 to stay idempotent on re-runs.
        self.stdout.write("  [17/17] Notifications (80–120 total)...")

        existing_count = Notification.objects.count()
        if existing_count < 80:
            batch = []

            # Targeted notifications for known accounts
            targeted = [
                (
                    student_demo_user,
                    "Your student account has been created. Welcome to the FYP Evaluation System.",
                ),
                (
                    student_demo_user,
                    "Your project 'Smart Clinic Queue Management System' has been approved!",
                ),
                (
                    student_demo_user,
                    "Your submission has been accepted. Judges will be assigned soon.",
                ),
                (
                    student_demo_user,
                    "Mr. Farhan Iskandar has been assigned to evaluate your project.",
                ),
                (
                    judge_demo_user,
                    "Your judge registration has been approved! Welcome, Mr. Farhan Iskandar.",
                ),
                (
                    judge_demo_user,
                    "You have been assigned to evaluate: Smart Clinic Queue Management System.",
                ),
                (
                    pic_user,
                    "New project registration received: Smart Clinic Queue Management System.",
                ),
                (pic_user, "New student registered: Adam Hakimi (student_demo)."),
                (pic_user, "New judge registered: Mr. Farhan Iskandar (judge_demo)."),
                (
                    pic_user,
                    "Evaluation form submitted by seed_judge_01 for: E-Learning Progress Tracker.",
                ),
                (
                    pic2_user,
                    "PIC Coordinator account is active. 12 projects are registered.",
                ),
            ]
            for user_obj, msg in targeted:
                if not Notification.objects.filter(user=user_obj, message=msg).exists():
                    batch.append(
                        Notification(user=user_obj, message=msg, is_read=False)
                    )

            # Bulk random notifications to reach 80–120
            target_total = random.randint(95, 115)
            remaining = max(0, target_total - existing_count - len(targeted))

            all_users = list(User.objects.filter(is_active=True))
            for j in range(remaining):
                u = all_users[j % len(all_users)]
                msg = NOTIF_MESSAGES[j % len(NOTIF_MESSAGES)]
                is_read = j % 3 != 0  # 2/3 are read
                batch.append(Notification(user=u, message=msg, is_read=is_read))

            Notification.objects.bulk_create(batch)
            self.stdout.write(f"      Created {len(batch)} notifications.")
        else:
            self.stdout.write(
                f"      Skipped — {existing_count} notifications already exist."
            )

        # ── Summary ───────────────────────────────────────────────────────────
        student_count = StudentProfile.objects.count()
        judge_count = JudgeProfile.objects.count()
        project_count = Project.objects.count()
        submission_count = ProjectSubmission.objects.count()
        assignment_count = JudgeAssignment.objects.count()
        eval_sub_count = EvaluationSubmission.objects.count()
        eval_accepted = EvaluationSubmission.objects.filter(status="accepted").count()
        eval_pending = EvaluationSubmission.objects.filter(
            status="pending_review"
        ).count()
        eval_rejected = EvaluationSubmission.objects.filter(status="rejected").count()
        not_submitted = assignment_count - eval_sub_count
        notif_count = Notification.objects.count()
        ann_count = Announcement.objects.count()
        deadline_count = Deadline.objects.count()

        self.stdout.write("\n" + self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  Demo data seeded successfully!"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Students          : {student_count}")
        self.stdout.write(f"  Judges            : {judge_count}")
        self.stdout.write(f"  Projects          : {project_count}")
        self.stdout.write(f"  Submissions       : {submission_count}")
        self.stdout.write(f"  Judge Assignments : {assignment_count}")
        self.stdout.write(
            f"  Eval forms subm.  : {eval_sub_count} ({eval_accepted} accepted, {eval_pending} pending, {eval_rejected} rejected)"
        )
        self.stdout.write(f"  Eval forms not sub: {not_submitted}")
        self.stdout.write(f"  Notifications     : {notif_count}")
        self.stdout.write(f"  Announcements     : {ann_count}")
        self.stdout.write(f"  Deadlines set     : {deadline_count}")
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "  ── Known Login Accounts ──────────────────────────────"
            )
        )
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("  PIC / Admin"))
        self.stdout.write("    Username : pic_demo")
        self.stdout.write("    Password : DemoPass123!")
        self.stdout.write("    Email    : pic.demo@unikl.edu.my")
        self.stdout.write("    Name     : Dr. Aina Rahman")
        self.stdout.write("    URL      : /login/ → /pic/dashboard/")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("  Student"))
        self.stdout.write("    Username : student_demo")
        self.stdout.write("    Password : DemoPass123!")
        self.stdout.write("    Email    : student.demo@unikl.edu.my")
        self.stdout.write("    Name     : Adam Hakimi  |  ID: 52211223344")
        self.stdout.write(
            "    Project  : Smart Clinic Queue Management System [Approved, Accepted]"
        )
        self.stdout.write("    URL      : /login/ → /student/dashboard/")
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("  Judge"))
        self.stdout.write("    Username : judge_demo")
        self.stdout.write("    Password : DemoPass123!")
        self.stdout.write("    Email    : judge.demo@unikl.edu.my")
        self.stdout.write("    Name     : Mr. Farhan Iskandar  |  Status: Approved")
        self.stdout.write("    Assigned : Smart Clinic Queue Management System")
        self.stdout.write(
            "    NOTE     : No evaluation submitted — log in to test the form manually"
        )
        self.stdout.write("    URL      : /login/ → /judge/dashboard/")
        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("  Start the server: python manage.py runserver")
        )
        self.stdout.write(self.style.SUCCESS("=" * 60 + "\n"))
