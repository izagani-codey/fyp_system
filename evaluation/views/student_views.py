from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from evaluation.decorators import deadline_active, role_required
from evaluation.forms import ProjectCreateForm, ProjectJoinForm, ProjectSubmissionForm
from evaluation.models import (
    Deadline,
    JudgeAssignment,
    Notification,
    Project,
    ProjectMember,
    ProjectSubmission,
    StudentProfile,
)
from evaluation.utils import notify


def _get_student_project(student):
    """
    Return the Project this student is involved with (as leader or member).
    Returns None if the student has no project yet.
    """
    # Check if they're a leader
    led = Project.objects.filter(leader=student).first()
    if led:
        return led
    # Check if they're a member
    membership = (
        ProjectMember.objects.filter(student=student).select_related("project").first()
    )
    if membership:
        return membership.project
    return None


@login_required
@role_required("student")
def student_dashboard_view(request):
    """
    Student dashboard showing:
    - Project registration status
    - Submission status
    - Deadline status
    - Unread notifications
    """
    student = request.user.student_profile
    project = _get_student_project(student)
    submission = None
    assignments = []

    if project:
        # Get submission if it exists
        try:
            submission = project.submission
        except ProjectSubmission.DoesNotExist:
            submission = None
        # Get judge assignments (but NOT scores — students cannot see marks)
        assignments = JudgeAssignment.objects.filter(project=project).select_related(
            "judge"
        )

    # Fetch deadlines for display
    deadlines = {d.deadline_type: d for d in Deadline.objects.filter(is_active=True)}

    # Fetch unread notifications (mark as read after fetching)
    notifications = list(
        Notification.objects.filter(user=request.user, is_read=False)[:10]
    )
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    # Get all project members if there is a project
    members = []
    if project:
        members = list(
            ProjectMember.objects.filter(project=project).select_related("student")
        )

    context = {
        "student": student,
        "project": project,
        "submission": submission,
        "assignments": assignments,
        "members": members,
        "deadlines": deadlines,
        "notifications": notifications,
        "is_leader": project and project.leader == student if project else False,
    }
    return render(request, "evaluation/student/dashboard.html", context)


@login_required
@role_required("student")
@deadline_active(
    "registration",
    redirect_url="student_dashboard",
    message="The project registration deadline has passed.",
)
def create_project_view(request):
    """
    Let a student register a new project as project leader.
    One student can only lead one project.
    """
    student = request.user.student_profile

    # Prevent creating a second project
    existing = _get_student_project(student)
    if existing:
        messages.warning(
            request,
            "You are already registered in a project. You cannot create another.",
        )
        return redirect("student_dashboard")

    if request.method == "POST":
        form = ProjectCreateForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.leader = student
            if not project.course:
                project.course = student.course
            if not project.programme and project.course:
                project.programme = project.course.name
            project.save()
            # Notify student
            notify(
                request.user,
                f"Your project '{project.title}' has been submitted for registration. "
                "Please wait for PIC approval.",
                email_subject="FYP System — Project Registration Submitted",
            )
            messages.success(
                request, f"Project '{project.title}' registered! Awaiting PIC approval."
            )
            return redirect("student_dashboard")
    else:
        form = ProjectCreateForm(
            initial={
                "course": student.course,
                "programme": student.programme
                or (student.course.name if student.course else ""),
                "section": student.section,
            }
        )

    return render(request, "evaluation/student/create_project.html", {"form": form})


@login_required
@role_required("student")
@deadline_active(
    "registration",
    redirect_url="student_dashboard",
    message="The project registration deadline has passed.",
)
def join_project_view(request):
    """
    Let a student join an existing project by entering the project ID.
    The student must not already be in a project.
    """
    student = request.user.student_profile

    # Prevent joining if already in a project
    existing = _get_student_project(student)
    if existing:
        messages.warning(request, "You are already registered in a project.")
        return redirect("student_dashboard")

    if request.method == "POST":
        form = ProjectJoinForm(request.POST)
        if form.is_valid():
            project_id = form.cleaned_data["project_id"]
            project = get_object_or_404(Project, pk=project_id)

            # Check not already a member
            if ProjectMember.objects.filter(project=project, student=student).exists():
                messages.warning(request, "You are already a member of this project.")
                return redirect("student_dashboard")

            # Cannot join your own project as a member (you'd be the leader)
            if project.leader == student:
                messages.warning(request, "You are already the leader of this project.")
                return redirect("student_dashboard")

            ProjectMember.objects.create(project=project, student=student)
            notify(
                request.user,
                f"You have joined project '{project.title}'.",
                email_subject="FYP System — Joined Project",
            )
            messages.success(request, f"Successfully joined project: {project.title}")
            return redirect("student_dashboard")
    else:
        form = ProjectJoinForm()

    return render(request, "evaluation/student/join_project.html", {"form": form})


@login_required
@role_required("student")
@deadline_active(
    "submission",
    redirect_url="student_dashboard",
    message="The abstract/video submission deadline has passed.",
)
def submit_project_view(request):
    """
    Let the project leader submit abstract and video.
    Only the project leader can submit (not regular members).
    The project must be approved first.
    """
    student = request.user.student_profile
    project = _get_student_project(student)

    if not project:
        messages.warning(request, "You do not have a project registered yet.")
        return redirect("student_dashboard")

    if project.leader != student:
        messages.warning(
            request, "Only the project leader can submit project materials."
        )
        return redirect("student_dashboard")

    if project.registration_status != "approved":
        messages.warning(
            request, "Your project must be approved before you can submit materials."
        )
        return redirect("student_dashboard")

    # Get or create submission record
    submission, _ = ProjectSubmission.objects.get_or_create(project=project)

    if submission.status == "accepted":
        messages.info(request, "Your submission has already been accepted by PIC.")
        return redirect("student_dashboard")

    if request.method == "POST":
        form = ProjectSubmissionForm(request.POST, request.FILES, instance=submission)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.status = "pending_review"
            sub.submitted_at = timezone.now()
            sub.save()
            notify(
                request.user,
                f"Your submission for '{project.title}' has been received and is pending review.",
                email_subject="FYP System — Submission Received",
            )
            messages.success(request, "Submission received! PIC will review it.")
            return redirect("student_dashboard")
    else:
        form = ProjectSubmissionForm(instance=submission)

    return render(
        request,
        "evaluation/student/submit_project.html",
        {
            "form": form,
            "project": project,
            "submission": submission,
        },
    )


@login_required
@role_required("student")
def student_notifications_view(request):
    """Show all notifications for this student (read and unread)."""
    all_notifications = Notification.objects.filter(user=request.user).order_by(
        "-created_at"
    )
    # Mark all as read when viewing this page
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(
        request,
        "evaluation/student/notifications.html",
        {
            "notifications": all_notifications,
        },
    )
