from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from evaluation.decorators import role_required, deadline_active
from evaluation.forms import EvaluationForm
from evaluation.models import (
    JudgeProfile, JudgeAssignment, ProjectMember, Notification,
)
from evaluation.utils import notify


@login_required
@role_required('judge')
def judge_dashboard_view(request):
    """
    Judge dashboard showing:
    - Registration/approval status
    - Pending and completed assignments
    """
    judge = request.user.judge_profile

    if judge.registration_status != 'approved':
        # Not yet approved — show pending status page
        return render(request, 'evaluation/judge/dashboard.html', {
            'judge': judge,
            'not_approved': True,
        })

    # Get all assignments for this judge
    all_assignments = JudgeAssignment.objects.filter(judge=judge).select_related(
        'project', 'project__leader', 'project__submission'
    )

    # Separate pending (no evaluation yet) from completed
    pending = []
    completed = []
    for a in all_assignments:
        if hasattr(a, 'evaluation'):
            completed.append(a)
        else:
            pending.append(a)

    # Fetch unread notifications
    notifications = list(Notification.objects.filter(user=request.user, is_read=False)[:5])
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    return render(request, 'evaluation/judge/dashboard.html', {
        'judge': judge,
        'not_approved': False,
        'pending_assignments': pending,
        'completed_assignments': completed,
        'notifications': notifications,
    })


@login_required
@role_required('judge')
def judge_project_detail_view(request, assignment_id):
    """
    Show full project details for a judge's assigned project:
    - Student/group info (all members)
    - Project title, programme, supervisor
    - Abstract text and PDF
    - Video link
    Judges CANNOT see scores from this view.
    """
    judge = request.user.judge_profile
    assignment = get_object_or_404(JudgeAssignment, id=assignment_id, judge=judge)
    project = assignment.project

    # Get all project members (leader + additional members)
    members = list(ProjectMember.objects.filter(project=project).select_related('student'))

    # Get submission safely
    try:
        submission = project.submission
    except Exception:
        submission = None

    already_evaluated = hasattr(assignment, 'evaluation')

    return render(request, 'evaluation/judge/project_detail.html', {
        'assignment': assignment,
        'project': project,
        'members': members,
        'submission': submission,
        'already_evaluated': already_evaluated,
    })


@login_required
@role_required('judge')
@deadline_active('evaluation', redirect_url='judge_dashboard',
                 message="The evaluation deadline has passed.")
def evaluate_view(request, assignment_id):
    """
    Judge fills in and submits the evaluation form for their assigned project.
    - Judges cannot re-submit after submitting once.
    - Judges cannot reject assignments.
    - Total score is auto-calculated on save.
    """
    judge = request.user.judge_profile
    assignment = get_object_or_404(JudgeAssignment, id=assignment_id, judge=judge)

    # Prevent re-submission
    if hasattr(assignment, 'evaluation'):
        messages.info(request, "You have already submitted an evaluation for this project.")
        return redirect('judge_dashboard')

    project = assignment.project

    # The project must have an accepted submission before evaluation
    try:
        submission = project.submission
        if submission.status != 'accepted':
            messages.warning(
                request,
                "This project's submission has not been accepted yet. Evaluation is not open."
            )
            return redirect('judge_dashboard')
    except Exception:
        messages.warning(request, "This project has no submission yet.")
        return redirect('judge_dashboard')

    members = list(ProjectMember.objects.filter(project=project).select_related('student'))

    if request.method == 'POST':
        form = EvaluationForm(request.POST)
        if form.is_valid():
            evaluation = form.save(commit=False)
            evaluation.assignment = assignment
            evaluation.save()  # total_score auto-calculated in model.save()

            # Notify the project leader that evaluation has been submitted
            notify(
                project.leader.user,
                f"Your project '{project.title}' has been evaluated.",
                email_subject="FYP System — Evaluation Submitted",
            )
            messages.success(
                request,
                f"Evaluation submitted successfully. Total: {evaluation.total_score}/95."
            )
            return redirect('judge_dashboard')
    else:
        form = EvaluationForm()

    return render(request, 'evaluation/judge/evaluate.html', {
        'form': form,
        'assignment': assignment,
        'project': project,
        'submission': submission,
        'members': members,
    })


@login_required
@role_required('judge')
def completed_evaluations_view(request):
    """
    Show the judge's completed evaluations.
    Shows which projects they evaluated and confirms submission.
    Does NOT show scores to other parties — but shows the judge their OWN submitted scores.
    """
    judge = request.user.judge_profile
    completed = JudgeAssignment.objects.filter(
        judge=judge
    ).select_related(
        'project', 'project__leader', 'evaluation'
    ).filter(evaluation__isnull=False)

    return render(request, 'evaluation/judge/completed_evaluations.html', {
        'judge': judge,
        'completed_assignments': completed,
    })
