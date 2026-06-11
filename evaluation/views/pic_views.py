from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone

from evaluation.decorators import pic_required
from evaluation.models import (
    Project, ProjectMember, ProjectSubmission,
    JudgeProfile, JudgeAssignment, Evaluation,
    Deadline, Announcement, Notification,
)
from evaluation.utils import notify, export_results_csv, get_project_average_score


# ── Dashboard ─────────────────────────────────────────────────────────────────

@pic_required
def pic_dashboard_view(request):
    """
    PIC overview dashboard with key statistics.
    Shows counts for projects, submissions, judges, and evaluations.
    """
    context = {
        'total_projects':       Project.objects.count(),
        'pending_projects':     Project.objects.filter(registration_status='pending').count(),
        'approved_projects':    Project.objects.filter(registration_status='approved').count(),
        'pending_submissions':  ProjectSubmission.objects.filter(status='pending_review').count(),
        'accepted_submissions': ProjectSubmission.objects.filter(status='accepted').count(),
        'approved_judges':      JudgeProfile.objects.filter(registration_status='approved').count(),
        'pending_evaluations':  JudgeAssignment.objects.filter(evaluation__isnull=True).count(),
        'completed_evaluations':Evaluation.objects.count(),
    }
    return render(request, 'evaluation/pic/dashboard.html', context)


# ── Project registrations ─────────────────────────────────────────────────────

@pic_required
def pic_project_registrations_view(request):
    """List all project registrations with optional status filter."""
    status_filter = request.GET.get('status', '')
    projects = Project.objects.select_related('leader').order_by('-created_at')
    if status_filter in ('pending', 'approved', 'rejected'):
        projects = projects.filter(registration_status=status_filter)
    return render(request, 'evaluation/pic/project_registrations.html', {
        'projects': projects,
        'status_filter': status_filter,
    })


@pic_required
def pic_approve_project_view(request, project_id):
    """Approve or reject a project registration via POST."""
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '').strip()
        project.pic_remarks = remarks

        if action == 'approve':
            project.registration_status = 'approved'
            project.save()
            # Auto-create a ProjectSubmission record for this project
            ProjectSubmission.objects.get_or_create(project=project)
            notify(
                project.leader.user,
                f"Your project '{project.title}' has been approved! "
                "You can now submit your abstract and video.",
                email_subject="FYP System — Project Registration Approved",
            )
            messages.success(request, f"Project '{project.title}' approved.")
        elif action == 'reject':
            project.registration_status = 'rejected'
            project.save()
            notify(
                project.leader.user,
                f"Your project '{project.title}' registration was rejected. "
                f"Reason: {remarks or 'No reason provided.'}",
                email_subject="FYP System — Project Registration Rejected",
            )
            messages.warning(request, f"Project '{project.title}' rejected.")

    return redirect('pic_project_registrations')


# ── Judge registrations ───────────────────────────────────────────────────────

@pic_required
def pic_judge_registrations_view(request):
    """List all judge registrations with optional status filter."""
    status_filter = request.GET.get('status', '')
    judges = JudgeProfile.objects.select_related('user').order_by('-created_at')
    if status_filter in ('pending', 'approved', 'rejected'):
        judges = judges.filter(registration_status=status_filter)
    return render(request, 'evaluation/pic/judge_registrations.html', {
        'judges': judges,
        'status_filter': status_filter,
    })


@pic_required
def pic_approve_judge_view(request, judge_id):
    """Approve or reject a judge registration via POST."""
    judge = get_object_or_404(JudgeProfile, id=judge_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            judge.registration_status = 'approved'
            judge.save()
            notify(
                judge.user,
                "Your judge registration has been approved! "
                "You can now log in and view your assigned projects.",
                email_subject="FYP System — Judge Registration Approved",
            )
            messages.success(request, f"Judge '{judge.full_name}' approved.")
        elif action == 'reject':
            judge.registration_status = 'rejected'
            judge.save()
            notify(
                judge.user,
                "Your judge registration has been rejected. "
                "Please contact the PIC for more information.",
                email_subject="FYP System — Judge Registration Rejected",
            )
            messages.warning(request, f"Judge '{judge.full_name}' rejected.")

    return redirect('pic_judge_registrations')


# ── Submissions ───────────────────────────────────────────────────────────────

@pic_required
def pic_submissions_view(request):
    """List projects whose submissions need review, plus all submission statuses."""
    status_filter = request.GET.get('status', '')
    submissions = ProjectSubmission.objects.select_related(
        'project', 'project__leader'
    ).exclude(status='not_submitted').order_by('-submitted_at')
    if status_filter in ('pending_review', 'accepted', 'rejected'):
        submissions = submissions.filter(status=status_filter)
    return render(request, 'evaluation/pic/submissions.html', {
        'submissions': submissions,
        'status_filter': status_filter,
    })


@pic_required
def pic_submission_detail_view(request, project_id):
    """PIC views the full submission details: abstract text, PDF file, video link."""
    project = get_object_or_404(Project, id=project_id)
    submission = get_object_or_404(ProjectSubmission, project=project)
    members = ProjectMember.objects.filter(project=project).select_related('student')
    return render(request, 'evaluation/pic/submission_detail.html', {
        'project': project,
        'submission': submission,
        'members': members,
    })


@pic_required
def pic_accept_submission_view(request, project_id):
    """Accept or reject a submitted project abstract/video via POST."""
    project = get_object_or_404(Project, id=project_id)
    submission = get_object_or_404(ProjectSubmission, project=project)

    if request.method == 'POST':
        action = request.POST.get('action')
        remarks = request.POST.get('remarks', '').strip()
        submission.pic_remarks = remarks
        submission.reviewed_at = timezone.now()

        if action == 'accept':
            submission.status = 'accepted'
            submission.save()
            notify(
                project.leader.user,
                f"Your submission for '{project.title}' has been accepted! "
                "Judges will be assigned soon.",
                email_subject="FYP System — Submission Accepted",
            )
            messages.success(request, "Submission accepted.")
        elif action == 'reject':
            submission.status = 'rejected'
            submission.save()
            notify(
                project.leader.user,
                f"Your submission for '{project.title}' was rejected. "
                f"Remarks: {remarks or 'No remarks provided.'}",
                email_subject="FYP System — Submission Rejected",
            )
            messages.warning(request, "Submission rejected.")

    return redirect('pic_submission_detail', project_id=project_id)


# ── Judge assignment ──────────────────────────────────────────────────────────

@pic_required
def pic_assign_judges_view(request, project_id):
    """
    PIC assigns one or more approved judges to a project.
    Existing assignments are shown and cannot be re-assigned.
    """
    project = get_object_or_404(Project, id=project_id)
    approved_judges = JudgeProfile.objects.filter(registration_status='approved')
    existing_judge_ids = set(
        JudgeAssignment.objects.filter(project=project).values_list('judge_id', flat=True)
    )

    if request.method == 'POST':
        judge_ids = request.POST.getlist('judge_ids')
        assigned_count = 0
        for jid in judge_ids:
            judge = get_object_or_404(JudgeProfile, id=jid)
            assignment, created = JudgeAssignment.objects.get_or_create(
                judge=judge, project=project
            )
            if created:
                assigned_count += 1
                notify(
                    judge.user,
                    f"You have been assigned to evaluate: '{project.title}'. "
                    "Please log in to view the project details.",
                    email_subject="FYP System — New Project Assignment",
                )
        if assigned_count:
            messages.success(request, f"{assigned_count} judge(s) assigned to '{project.title}'.")
        else:
            messages.info(request, "No new judges were assigned (already assigned or none selected).")
        return redirect('pic_assign_judges', project_id=project_id)

    members = ProjectMember.objects.filter(project=project).select_related('student')
    return render(request, 'evaluation/pic/assign_judges.html', {
        'project': project,
        'approved_judges': approved_judges,
        'existing_judge_ids': existing_judge_ids,
        'members': members,
    })


# ── Evaluation tracking ───────────────────────────────────────────────────────

@pic_required
def pic_evaluations_view(request):
    """
    PIC tracks pending and completed evaluations across all projects.
    Shows which assignments have been evaluated and which are still pending.
    """
    all_assignments = JudgeAssignment.objects.select_related(
        'judge', 'project', 'project__leader'
    ).order_by('project__title', 'judge__full_name')

    pending = [a for a in all_assignments if not hasattr(a, 'evaluation')]
    completed = [a for a in all_assignments if hasattr(a, 'evaluation')]

    return render(request, 'evaluation/pic/evaluations.html', {
        'pending_assignments': pending,
        'completed_assignments': completed,
    })


# ── Results ───────────────────────────────────────────────────────────────────

@pic_required
def pic_results_view(request):
    """
    Compiled results page (PIC only — scores are private).
    Shows all approved projects with their average evaluation scores.
    """
    projects = Project.objects.filter(
        registration_status='approved'
    ).prefetch_related(
        'assignments__evaluation', 'assignments__judge', 'members__student'
    ).select_related('leader').order_by('title')

    results = []
    for project in projects:
        avg = get_project_average_score(project)
        evaluations = [
            a.evaluation for a in project.assignments.all()
            if hasattr(a, 'evaluation')
        ]
        results.append({
            'project': project,
            'average_score': avg,
            'evaluation_count': len(evaluations),
            'evaluations': evaluations,
        })

    return render(request, 'evaluation/pic/results.html', {'results': results})


@pic_required
def pic_export_csv_view(request):
    """Download evaluation results as CSV."""
    return export_results_csv()


# ── Deadlines ─────────────────────────────────────────────────────────────────

@pic_required
def pic_deadlines_view(request):
    """
    PIC sets or updates the three deadlines:
    registration, submission, evaluation.
    Each deadline_type is unique — update if exists, create if not.
    """
    from evaluation.forms import DeadlineForm
    deadlines = {d.deadline_type: d for d in Deadline.objects.all()}
    deadline_types = [
        ('registration', 'Project Registration Deadline'),
        ('submission', 'Abstract/Video Submission Deadline'),
        ('evaluation', 'Evaluation Deadline'),
    ]

    if request.method == 'POST':
        deadline_type = request.POST.get('deadline_type')
        existing = deadlines.get(deadline_type)
        form = DeadlineForm(request.POST, instance=existing)
        if form.is_valid():
            deadline = form.save(commit=False)
            deadline.deadline_type = deadline_type
            deadline.save()
            messages.success(
                request,
                f"{deadline.get_deadline_type_display()} updated to "
                f"{deadline.deadline_date.strftime('%d %b %Y %H:%M')}."
            )
            return redirect('pic_deadlines')
        else:
            messages.error(request, "Invalid deadline. Please check the date/time.")

    return render(request, 'evaluation/pic/deadlines.html', {
        'deadlines': deadlines,
        'deadline_types': deadline_types,
    })


# ── Announcements ─────────────────────────────────────────────────────────────

@pic_required
def pic_announcements_view(request):
    """
    PIC creates or edits announcements.
    Announcements can be marked as is_winners and is_published.
    GET: list all announcements with a create form.
    POST: save new or update existing announcement.
    """
    from evaluation.forms import AnnouncementForm
    announcements = Announcement.objects.all().order_by('-created_at')
    edit_id = request.GET.get('edit')
    edit_obj = None
    if edit_id:
        edit_obj = get_object_or_404(Announcement, id=edit_id)

    if request.method == 'POST':
        ann_id = request.POST.get('announcement_id')
        if ann_id:
            # Editing existing
            ann_obj = get_object_or_404(Announcement, id=ann_id)
            form = AnnouncementForm(request.POST, instance=ann_obj)
        else:
            # Creating new
            form = AnnouncementForm(request.POST)

        if form.is_valid():
            ann = form.save(commit=False)
            if not ann.created_by_id:
                ann.created_by = request.user
            if ann.is_published and not ann.published_at:
                ann.published_at = timezone.now()
                # Notify all registered users that an announcement was published
                _notify_all_users(ann)
            ann.save()
            messages.success(request, f"Announcement '{ann.title}' saved.")
            return redirect('pic_announcements')
        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = AnnouncementForm(instance=edit_obj)

    return render(request, 'evaluation/pic/announcements.html', {
        'announcements': announcements,
        'form': form,
        'edit_obj': edit_obj,
    })


@pic_required
def pic_announcement_toggle_publish_view(request, announcement_id):
    """Toggle publish/unpublish an announcement via POST."""
    ann = get_object_or_404(Announcement, id=announcement_id)
    if request.method == 'POST':
        ann.is_published = not ann.is_published
        if ann.is_published and not ann.published_at:
            ann.published_at = timezone.now()
            _notify_all_users(ann)
        ann.save()
        status = "published" if ann.is_published else "unpublished"
        messages.success(request, f"Announcement '{ann.title}' {status}.")
    return redirect('pic_announcements')


def _notify_all_users(announcement):
    """Helper: send in-app notification to all registered users about a published announcement."""
    from django.contrib.auth.models import User
    for user in User.objects.filter(is_active=True):
        notify(
            user,
            f"New announcement: {announcement.title}",
            email_subject="FYP System — New Announcement",
            email_body=f"New announcement posted:\n\n{announcement.title}\n\n{announcement.content}",
        )
