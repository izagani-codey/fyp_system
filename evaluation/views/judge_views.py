from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from evaluation.decorators import deadline_active, role_required
from evaluation.forms import EvaluationSubmissionForm
from evaluation.models import (
    EvaluationScore,
    EvaluationSubmission,
    EvaluationTemplate,
    JudgeAssignment,
    Notification,
    ProjectMember,
)
from evaluation.utils import notify


@login_required
@role_required("judge")
def judge_dashboard_view(request):
    judge = request.user.judge_profile

    if judge.registration_status != "approved":
        return render(
            request,
            "evaluation/judge/dashboard.html",
            {
                "judge": judge,
                "not_approved": True,
            },
        )

    all_assignments = JudgeAssignment.objects.filter(judge=judge).select_related(
        "project", "project__leader", "project__course", "project__submission"
    )

    pending = []  # no submission yet
    submitted = []  # pending_review or accepted or rejected

    for assignment in all_assignments:
        try:
            assignment.eval_submission
            submitted.append(assignment)
        except EvaluationSubmission.DoesNotExist:
            pending.append(assignment)

    notifications = list(
        Notification.objects.filter(user=request.user, is_read=False)[:5]
    )
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    return render(
        request,
        "evaluation/judge/dashboard.html",
        {
            "judge": judge,
            "not_approved": False,
            "pending_assignments": pending,
            "submitted_assignments": submitted,
            "notifications": notifications,
        },
    )


@login_required
@role_required("judge")
def judge_project_detail_view(request, assignment_id):
    """Show full project details: student/group info, abstract, video, template download."""
    judge = request.user.judge_profile
    assignment = get_object_or_404(
        JudgeAssignment.objects.select_related("project__course", "project__leader"),
        id=assignment_id,
        judge=judge,
    )
    project = assignment.project

    members = list(
        ProjectMember.objects.filter(project=project).select_related(
            "student", "student__course"
        )
    )

    try:
        submission = project.submission
    except Exception:
        submission = None

    try:
        eval_submission = assignment.eval_submission
    except EvaluationSubmission.DoesNotExist:
        eval_submission = None

    active_template = (
        EvaluationTemplate.objects.filter(is_active=True)
        .prefetch_related("criteria")
        .first()
    )

    return render(
        request,
        "evaluation/judge/project_detail.html",
        {
            "assignment": assignment,
            "project": project,
            "members": members,
            "submission": submission,
            "eval_submission": eval_submission,
            "active_template": active_template,
        },
    )


@login_required
@role_required("judge")
@deadline_active(
    "evaluation",
    redirect_url="judge_dashboard",
    message="The evaluation deadline has passed.",
)
def submit_evaluation_view(request, assignment_id):
    """
    Judge submits scores against the active template.
    Rejected submissions can be corrected and resubmitted.
    """
    judge = request.user.judge_profile
    assignment = get_object_or_404(
        JudgeAssignment.objects.select_related("project__leader", "project__course"),
        id=assignment_id,
        judge=judge,
    )

    try:
        existing = assignment.eval_submission
    except EvaluationSubmission.DoesNotExist:
        existing = None

    if existing:
        if existing.status == "accepted":
            messages.info(request, "Your evaluation has been accepted by PIC.")
            return redirect("judge_dashboard")
        if existing.status == "pending_review":
            messages.info(request, "Your evaluation is currently under PIC review.")
            return redirect("judge_dashboard")
        # status == 'rejected' → allow resubmit

    project = assignment.project

    try:
        project_submission = project.submission
        if project_submission.status != "accepted":
            messages.warning(
                request,
                "This project's materials have not been accepted yet. Evaluation is not open.",
            )
            return redirect("judge_dashboard")
    except Exception:
        messages.warning(request, "This project has no submission yet.")
        return redirect("judge_dashboard")

    active_template = (
        EvaluationTemplate.objects.filter(is_active=True)
        .prefetch_related("criteria")
        .first()
    )
    if not active_template:
        messages.warning(request, "PIC has not activated an evaluation template yet.")
        return redirect("judge_project_detail", assignment_id=assignment.id)
    if not active_template.criteria.exists():
        messages.warning(
            request,
            "The active evaluation template has no criteria yet. Please contact PIC.",
        )
        return redirect("judge_project_detail", assignment_id=assignment.id)

    members = list(
        ProjectMember.objects.filter(project=project).select_related(
            "student", "student__course"
        )
    )

    if request.method == "POST":
        form = EvaluationSubmissionForm(
            active_template, request.POST, request.FILES, instance=existing
        )
        if form.is_valid():
            sub = form.save(commit=False)
            sub.assignment = assignment
            sub.template = active_template
            sub.status = "pending_review"
            sub.submitted_at = timezone.now()
            # Reset review fields on (re)submit
            sub.reviewed_by = None
            sub.reviewed_at = None
            sub.pic_feedback = ""
            sub.save()

            # Replace previous scores so resubmissions exactly match the current form.
            sub.scores.all().delete()
            for criterion, score in form.score_items():
                score_obj = EvaluationScore(
                    submission=sub, criterion=criterion, score=score
                )
                score_obj.full_clean()
                score_obj.save()
            sub.recalculate_total()

            is_resubmit = existing is not None
            action_word = "resubmitted" if is_resubmit else "submitted"

            # Notify all PIC users
            for pic_user in User.objects.filter(profile__role="pic", is_active=True):
                notify(
                    pic_user,
                    f"Judge {judge.full_name} has {action_word} an evaluation "
                    f"for '{project.title}'.",
                    email_subject="FYP System — Evaluation Submitted",
                )

            messages.success(
                request, f"Evaluation {action_word} successfully. Awaiting PIC review."
            )
            return redirect("judge_dashboard")
    else:
        form = EvaluationSubmissionForm(active_template, instance=existing)

    return render(
        request,
        "evaluation/judge/submit_evaluation.html",
        {
            "form": form,
            "assignment": assignment,
            "project": project,
            "project_submission": project_submission,
            "members": members,
            "existing": existing,
            "active_template": active_template,
        },
    )


@login_required
@role_required("judge")
def judge_submissions_view(request):
    """Show all evaluation submissions by this judge with their current status."""
    judge = request.user.judge_profile
    assignments = JudgeAssignment.objects.filter(judge=judge).select_related(
        "project", "project__leader", "project__course"
    )

    submitted = []
    unsubmitted = []
    for assignment in assignments:
        try:
            submitted.append((assignment, assignment.eval_submission))
        except EvaluationSubmission.DoesNotExist:
            unsubmitted.append(assignment)

    return render(
        request,
        "evaluation/judge/submissions.html",
        {
            "judge": judge,
            "submitted": submitted,
            "unsubmitted": unsubmitted,
        },
    )
