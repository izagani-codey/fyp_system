from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from evaluation.decorators import pic_required
from evaluation.forms import (
    CourseForm,
    EvaluationCriterionForm,
    EvaluationReviewForm,
    EvaluationTemplateForm,
)
from evaluation.models import (
    Announcement,
    Course,
    Deadline,
    EvaluationCriterion,
    EvaluationSubmission,
    EvaluationTemplate,
    JudgeAssignment,
    JudgeProfile,
    Notification,
    Project,
    ProjectMember,
    ProjectSubmission,
)
from evaluation.utils import (
    export_results_csv,
    generate_top3_content,
    notify,
    ranked_project_results,
)

# ── Dashboard ─────────────────────────────────────────────────────────────────


@pic_required
def pic_dashboard_view(request):
    course_id = request.GET.get("course", "")
    courses = Course.objects.filter(is_active=True)
    projects = Project.objects.all()
    if course_id:
        projects = projects.filter(course_id=course_id)

    context = {
        "courses": courses,
        "course_filter": course_id,
        "total_projects": projects.count(),
        "pending_projects": projects.filter(registration_status="pending").count(),
        "approved_projects": projects.filter(registration_status="approved").count(),
        "pending_submissions": ProjectSubmission.objects.filter(
            project__in=projects, status="pending_review"
        ).count(),
        "accepted_submissions": ProjectSubmission.objects.filter(
            project__in=projects, status="accepted"
        ).count(),
        "approved_judges": JudgeProfile.objects.filter(
            registration_status="approved"
        ).count(),
        "pending_eval_forms": EvaluationSubmission.objects.filter(
            assignment__project__in=projects, status="pending_review"
        ).count(),
        "accepted_eval_forms": EvaluationSubmission.objects.filter(
            assignment__project__in=projects, status="accepted"
        ).count(),
        "unsubmitted_assignments": JudgeAssignment.objects.filter(
            project__in=projects, eval_submission__isnull=True
        ).count(),
    }
    return render(request, "evaluation/pic/dashboard.html", context)


# ── Project registrations ─────────────────────────────────────────────────────


@pic_required
def pic_project_registrations_view(request):
    status_filter = request.GET.get("status", "")
    course_filter = request.GET.get("course", "")
    projects = Project.objects.select_related("leader", "course").order_by(
        "-created_at"
    )
    if status_filter in ("pending", "approved", "rejected"):
        projects = projects.filter(registration_status=status_filter)
    if course_filter:
        projects = projects.filter(course_id=course_filter)
    return render(
        request,
        "evaluation/pic/project_registrations.html",
        {
            "projects": projects,
            "status_filter": status_filter,
            "course_filter": course_filter,
            "courses": Course.objects.filter(is_active=True),
        },
    )


@pic_required
def pic_approve_project_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == "POST":
        action = request.POST.get("action")
        remarks = request.POST.get("remarks", "").strip()
        project.pic_remarks = remarks

        if action == "approve":
            project.registration_status = "approved"
            project.save()
            ProjectSubmission.objects.get_or_create(project=project)
            notify(
                project.leader.user,
                f"Your project '{project.title}' has been approved! "
                "You can now submit your abstract and video.",
                email_subject="FYP System — Project Registration Approved",
            )
            messages.success(request, f"Project '{project.title}' approved.")
        elif action == "reject":
            project.registration_status = "rejected"
            project.save()
            notify(
                project.leader.user,
                f"Your project '{project.title}' registration was rejected. "
                f"Reason: {remarks or 'No reason provided.'}",
                email_subject="FYP System — Project Registration Rejected",
            )
            messages.warning(request, f"Project '{project.title}' rejected.")

    return redirect("pic_project_registrations")


# ── Judge registrations ───────────────────────────────────────────────────────


@pic_required
def pic_judge_registrations_view(request):
    status_filter = request.GET.get("status", "")
    judges = JudgeProfile.objects.select_related("user").order_by("-created_at")
    if status_filter in ("pending", "approved", "rejected"):
        judges = judges.filter(registration_status=status_filter)
    return render(
        request,
        "evaluation/pic/judge_registrations.html",
        {
            "judges": judges,
            "status_filter": status_filter,
        },
    )


@pic_required
def pic_approve_judge_view(request, judge_id):
    judge = get_object_or_404(JudgeProfile, id=judge_id)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve":
            judge.registration_status = "approved"
            judge.save()
            notify(
                judge.user,
                "Your judge registration has been approved! "
                "You can now log in and view your assigned projects.",
                email_subject="FYP System — Judge Registration Approved",
            )
            messages.success(request, f"Judge '{judge.full_name}' approved.")
        elif action == "reject":
            judge.registration_status = "rejected"
            judge.save()
            notify(
                judge.user,
                "Your judge registration has been rejected. "
                "Please contact the PIC for more information.",
                email_subject="FYP System — Judge Registration Rejected",
            )
            messages.warning(request, f"Judge '{judge.full_name}' rejected.")

    return redirect("pic_judge_registrations")


# ── Project material submissions ──────────────────────────────────────────────


@pic_required
def pic_submissions_view(request):
    status_filter = request.GET.get("status", "")
    course_filter = request.GET.get("course", "")
    submissions = (
        ProjectSubmission.objects.select_related(
            "project", "project__leader", "project__course"
        )
        .exclude(status="not_submitted")
        .order_by("-submitted_at")
    )
    if status_filter in ("pending_review", "accepted", "rejected"):
        submissions = submissions.filter(status=status_filter)
    if course_filter:
        submissions = submissions.filter(project__course_id=course_filter)
    return render(
        request,
        "evaluation/pic/submissions.html",
        {
            "submissions": submissions,
            "status_filter": status_filter,
            "course_filter": course_filter,
            "courses": Course.objects.filter(is_active=True),
        },
    )


@pic_required
def pic_submission_detail_view(request, project_id):
    project = get_object_or_404(
        Project.objects.select_related("course", "leader"), id=project_id
    )
    submission = get_object_or_404(ProjectSubmission, project=project)
    members = ProjectMember.objects.filter(project=project).select_related(
        "student", "student__course"
    )
    return render(
        request,
        "evaluation/pic/submission_detail.html",
        {
            "project": project,
            "submission": submission,
            "members": members,
        },
    )


@pic_required
def pic_accept_submission_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    submission = get_object_or_404(ProjectSubmission, project=project)

    if request.method == "POST":
        action = request.POST.get("action")
        remarks = request.POST.get("remarks", "").strip()
        submission.pic_remarks = remarks
        submission.reviewed_at = timezone.now()

        if action == "accept":
            submission.status = "accepted"
            submission.save()
            notify(
                project.leader.user,
                f"Your submission for '{project.title}' has been accepted! "
                "Judges will be assigned soon.",
                email_subject="FYP System — Submission Accepted",
            )
            messages.success(request, "Submission accepted.")
        elif action == "reject":
            submission.status = "rejected"
            submission.save()
            notify(
                project.leader.user,
                f"Your submission for '{project.title}' was rejected. "
                f"Remarks: {remarks or 'No remarks provided.'}",
                email_subject="FYP System — Submission Rejected",
            )
            messages.warning(request, "Submission rejected.")

    return redirect("pic_submission_detail", project_id=project_id)


# ── Judge assignment ──────────────────────────────────────────────────────────


@pic_required
def pic_assign_judges_view(request, project_id):
    project = get_object_or_404(
        Project.objects.select_related("course", "leader"), id=project_id
    )
    approved_judges = JudgeProfile.objects.filter(registration_status="approved")
    existing_judge_ids = set(
        JudgeAssignment.objects.filter(project=project).values_list(
            "judge_id", flat=True
        )
    )

    if request.method == "POST":
        judge_ids = request.POST.getlist("judge_ids")
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
                    "Please log in to view the project details and complete the active evaluation rubric.",
                    email_subject="FYP System — New Project Assignment",
                )
        if assigned_count:
            messages.success(
                request, f"{assigned_count} judge(s) assigned to '{project.title}'."
            )
        else:
            messages.info(
                request,
                "No new judges were assigned (already assigned or none selected).",
            )
        return redirect("pic_assign_judges", project_id=project_id)

    members = ProjectMember.objects.filter(project=project).select_related(
        "student", "student__course"
    )
    return render(
        request,
        "evaluation/pic/assign_judges.html",
        {
            "project": project,
            "approved_judges": approved_judges,
            "existing_judge_ids": existing_judge_ids,
            "members": members,
        },
    )


# ── Evaluation review ─────────────────────────────────────────────────────────


@pic_required
def pic_evaluations_view(request):
    """List evaluation submissions with status/course filters, plus unsubmitted assignments."""
    status_filter = request.GET.get("status", "")
    course_filter = request.GET.get("course", "")

    eval_submissions = EvaluationSubmission.objects.select_related(
        "assignment__judge",
        "assignment__project",
        "assignment__project__course",
        "reviewed_by",
        "template",
    ).order_by("-submitted_at")

    if status_filter in ("pending_review", "accepted", "rejected"):
        eval_submissions = eval_submissions.filter(status=status_filter)
    if course_filter:
        eval_submissions = eval_submissions.filter(
            assignment__project__course_id=course_filter
        )

    unsubmitted = JudgeAssignment.objects.filter(
        eval_submission__isnull=True
    ).select_related("judge", "project", "project__course")
    if course_filter:
        unsubmitted = unsubmitted.filter(project__course_id=course_filter)

    return render(
        request,
        "evaluation/pic/evaluations.html",
        {
            "eval_submissions": eval_submissions,
            "unsubmitted": unsubmitted,
            "status_filter": status_filter,
            "course_filter": course_filter,
            "courses": Course.objects.filter(is_active=True),
        },
    )


@pic_required
def pic_review_evaluation_view(request, submission_id):
    """PIC views scores/files and accepts or rejects an evaluation submission."""
    sub = get_object_or_404(
        EvaluationSubmission.objects.select_related(
            "assignment__judge",
            "assignment__project",
            "assignment__project__course",
            "template",
            "reviewed_by",
        ).prefetch_related("scores__criterion"),
        id=submission_id,
    )

    if request.method == "POST":
        form = EvaluationReviewForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data["action"]
            feedback = form.cleaned_data.get("pic_feedback", "").strip()
            sub.pic_feedback = feedback
            sub.reviewed_by = request.user
            sub.reviewed_at = timezone.now()

            if action == "accept":
                sub.status = "accepted"
                sub.save()
                notify(
                    sub.assignment.judge.user,
                    f"Your evaluation for '{sub.assignment.project.title}' "
                    "has been accepted by PIC.",
                    email_subject="FYP System — Evaluation Accepted",
                )
                messages.success(request, "Evaluation accepted.")
            elif action == "reject":
                sub.status = "rejected"
                sub.save()
                notify(
                    sub.assignment.judge.user,
                    f"Your evaluation for '{sub.assignment.project.title}' "
                    f"was rejected. Feedback: {feedback}",
                    email_subject="FYP System — Evaluation Rejected",
                )
                messages.warning(
                    request, "Evaluation rejected. Judge has been notified."
                )

            return redirect("pic_evaluations")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = EvaluationReviewForm()

    members = ProjectMember.objects.filter(
        project=sub.assignment.project
    ).select_related("student", "student__course")

    return render(
        request,
        "evaluation/pic/evaluation_review.html",
        {
            "sub": sub,
            "form": form,
            "members": members,
        },
    )


# ── Evaluation templates and criteria ─────────────────────────────────────────


@pic_required
def pic_eval_templates_view(request):
    """PIC manages dynamic evaluation templates, files, and criteria."""
    templates = EvaluationTemplate.objects.prefetch_related("criteria").order_by(
        "-created_at"
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create_template":
            form = EvaluationTemplateForm(request.POST, request.FILES)
            if form.is_valid():
                template = form.save(commit=False)
                template.created_by = request.user
                template.save()
                messages.success(request, f"Template '{template.title}' saved.")
                return redirect("pic_eval_templates")
            messages.error(request, "Please correct the template form errors below.")

        elif action == "set_active":
            template = get_object_or_404(
                EvaluationTemplate, id=request.POST.get("template_id")
            )
            template.is_active = True
            template.save()
            messages.success(request, f"Template '{template.title}' is now active.")
            return redirect("pic_eval_templates")

        elif action == "add_criterion":
            template = get_object_or_404(
                EvaluationTemplate, id=request.POST.get("template_id")
            )
            criterion_form = EvaluationCriterionForm(request.POST)
            if criterion_form.is_valid():
                criterion = criterion_form.save(commit=False)
                criterion.template = template
                criterion.save()
                messages.success(request, f"Criterion '{criterion.name}' added.")
                return redirect("pic_eval_templates")
            messages.error(request, "Please correct the criterion form errors below.")

        elif action == "edit_criterion":
            criterion = get_object_or_404(
                EvaluationCriterion, id=request.POST.get("criterion_id")
            )
            criterion_form = EvaluationCriterionForm(request.POST, instance=criterion)
            if criterion_form.is_valid():
                criterion_form.save()
                messages.success(request, f"Criterion '{criterion.name}' updated.")
                return redirect("pic_eval_templates")
            messages.error(request, "Please correct the criterion form errors below.")

        elif action == "delete_criterion":
            criterion = get_object_or_404(
                EvaluationCriterion, id=request.POST.get("criterion_id")
            )
            name = criterion.name
            criterion.delete()
            messages.success(request, f"Criterion '{name}' deleted.")
            return redirect("pic_eval_templates")
    else:
        form = EvaluationTemplateForm()
        criterion_form = EvaluationCriterionForm()

    return render(
        request,
        "evaluation/pic/eval_templates.html",
        {
            "templates": templates,
            "form": locals().get("form", EvaluationTemplateForm()),
            "criterion_form": locals().get("criterion_form", EvaluationCriterionForm()),
        },
    )


@pic_required
def pic_toggle_template_active_view(request, template_id):
    """Backward-compatible URL: set a template as the single active rubric."""
    template = get_object_or_404(EvaluationTemplate, id=template_id)
    if request.method == "POST":
        template.is_active = True
        template.save()
        messages.success(request, f"Template '{template.title}' is now active.")
    return redirect("pic_eval_templates")


# ── Results ───────────────────────────────────────────────────────────────────


@pic_required
def pic_results_view(request):
    """
    Compiled PIC-only results.
    Final scores use accepted evaluation submissions only; multiple judges are averaged.
    """
    course_filter = request.GET.get("course", "")
    course = None
    if course_filter:
        course = get_object_or_404(Course, id=course_filter)
    results = ranked_project_results(course=course)

    return render(
        request,
        "evaluation/pic/results.html",
        {
            "results": results,
            "courses": Course.objects.filter(is_active=True),
            "course_filter": course_filter,
        },
    )


@pic_required
def pic_generate_top3_announcement_view(request):
    """Generate and publish an overall or course-based Top 3 announcement."""
    if request.method == "POST":
        course_id = request.POST.get("course_id")
        course = get_object_or_404(Course, id=course_id) if course_id else None
        title, content = generate_top3_content(course=course)
        if not content:
            messages.warning(
                request,
                "No accepted evaluation scores are available for Top 3 generation.",
            )
            return redirect("pic_results")
        announcement = Announcement.objects.create(
            title=title,
            content=content,
            is_winners=True,
            is_published=True,
            published_at=timezone.now(),
            created_by=request.user,
        )
        _notify_all_users(announcement)
        messages.success(request, f"Published announcement: {announcement.title}")
    return redirect("pic_results")


@pic_required
def pic_export_csv_view(request):
    course = None
    course_id = request.GET.get("course")
    if course_id:
        course = get_object_or_404(Course, id=course_id)
    return export_results_csv(course=course)


# ── Deadlines ─────────────────────────────────────────────────────────────────


@pic_required
def pic_deadlines_view(request):
    from evaluation.forms import DeadlineForm

    deadlines = {d.deadline_type: d for d in Deadline.objects.all()}
    deadline_types = [
        ("registration", "Project Registration Deadline"),
        ("submission", "Abstract/Video Submission Deadline"),
        ("evaluation", "Evaluation Deadline"),
    ]

    if request.method == "POST":
        deadline_type = request.POST.get("deadline_type")
        existing = deadlines.get(deadline_type)
        form = DeadlineForm(request.POST, instance=existing)
        if form.is_valid():
            deadline = form.save(commit=False)
            deadline.deadline_type = deadline_type
            deadline.save()
            messages.success(
                request,
                f"{deadline.get_deadline_type_display()} updated to "
                f"{deadline.deadline_date.strftime('%d %b %Y %H:%M')}.",
            )
            return redirect("pic_deadlines")
        else:
            messages.error(request, "Invalid deadline. Please check the date/time.")

    return render(
        request,
        "evaluation/pic/deadlines.html",
        {
            "deadlines": deadlines,
            "deadline_types": deadline_types,
        },
    )


# ── Announcements ─────────────────────────────────────────────────────────────


@pic_required
def pic_announcements_view(request):
    from evaluation.forms import AnnouncementForm

    announcements = Announcement.objects.all().order_by("-created_at")
    edit_id = request.GET.get("edit")
    edit_obj = None
    if edit_id:
        edit_obj = get_object_or_404(Announcement, id=edit_id)

    if request.method == "POST":
        ann_id = request.POST.get("announcement_id")
        if ann_id:
            ann_obj = get_object_or_404(Announcement, id=ann_id)
            form = AnnouncementForm(request.POST, instance=ann_obj)
        else:
            form = AnnouncementForm(request.POST)

        if form.is_valid():
            ann = form.save(commit=False)
            if not ann.created_by_id:
                ann.created_by = request.user
            if ann.is_published and not ann.published_at:
                ann.published_at = timezone.now()
                _notify_all_users(ann)
            ann.save()
            messages.success(request, f"Announcement '{ann.title}' saved.")
            return redirect("pic_announcements")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AnnouncementForm(instance=edit_obj)

    return render(
        request,
        "evaluation/pic/announcements.html",
        {
            "announcements": announcements,
            "form": form,
            "edit_obj": edit_obj,
        },
    )


@pic_required
def pic_announcement_toggle_publish_view(request, announcement_id):
    ann = get_object_or_404(Announcement, id=announcement_id)
    if request.method == "POST":
        ann.is_published = not ann.is_published
        if ann.is_published and not ann.published_at:
            ann.published_at = timezone.now()
            _notify_all_users(ann)
        ann.save()
        status = "published" if ann.is_published else "unpublished"
        messages.success(request, f"Announcement '{ann.title}' {status}.")
    return redirect("pic_announcements")


def _notify_all_users(announcement):
    from django.contrib.auth.models import User

    for user in User.objects.filter(is_active=True):
        notify(
            user,
            f"New announcement: {announcement.title}",
            email_subject="FYP System — New Announcement",
            email_body=f"New announcement posted:\n\n{announcement.title}\n\n{announcement.content}",
        )


# ── Course Management ───────────────────────────────────────────────────────────


@pic_required
def pic_courses_view(request):
    """PIC manages courses: view, add, edit, activate/deactivate."""
    courses = Course.objects.all().order_by("name")
    edit_id = request.GET.get("edit")
    edit_obj = None
    if edit_id:
        edit_obj = get_object_or_404(Course, id=edit_id)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "create":
            form = CourseForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, f"Course '{form.cleaned_data['name']}' created.")
                return redirect("pic_courses")
            messages.error(request, "Please correct the errors below.")

        elif action == "edit":
            course = get_object_or_404(Course, id=request.POST.get("course_id"))
            form = CourseForm(request.POST, instance=course)
            if form.is_valid():
                form.save()
                messages.success(request, f"Course '{course.name}' updated.")
                return redirect("pic_courses")
            messages.error(request, "Please correct the errors below.")

        elif action == "toggle_active":
            course = get_object_or_404(Course, id=request.POST.get("course_id"))
            course.is_active = not course.is_active
            course.save()
            status = "activated" if course.is_active else "deactivated"
            messages.success(request, f"Course '{course.name}' {status}.")
            return redirect("pic_courses")

    else:
        form = CourseForm(instance=edit_obj)

    return render(
        request,
        "evaluation/pic/courses.html",
        {
            "courses": courses,
            "form": form,
            "edit_obj": edit_obj,
        },
    )
