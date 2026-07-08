from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg
from django.utils import timezone


class UserProfile(models.Model):
    """Extends Django's built-in User with a role."""

    ROLE_CHOICES = [
        ("student", "Student"),
        ("judge", "Judge"),
        ("pic", "PIC"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Course(models.Model):
    """Course/programme grouping used to separate projects and results."""

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class StudentProfile(models.Model):
    """Extra data for a student user."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    programme = models.CharField(max_length=100, blank=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
    )
    section = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"


class JudgeProfile(models.Model):
    """Extra data for a judge user."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="judge_profile"
    )
    full_name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    expertise_area = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20)
    registration_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.department})"


class Project(models.Model):
    """
    A FYP project/group — the main evaluation unit.
    One or more students belong to a project.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    title = models.CharField(max_length=255)
    programme = models.CharField(max_length=100, blank=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
    )
    section = models.CharField(max_length=50)
    supervisor_name = models.CharField(max_length=150)
    # The student who created the project and acts as leader
    leader = models.ForeignKey(
        "StudentProfile", on_delete=models.CASCADE, related_name="led_projects"
    )
    registration_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="pending"
    )
    pic_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def final_average_score(self):
        """Average accepted evaluation score only; returns None if no accepted scores exist."""
        return self.assignments.filter(eval_submission__status="accepted").aggregate(
            avg=Avg("eval_submission__total_score")
        )["avg"]

    def __str__(self):
        return f"{self.title} [{self.get_registration_status_display()}]"


class ProjectMember(models.Model):
    """Links additional student members to a project (the leader is tracked on Project.leader)."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="members"
    )
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="memberships"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "student")

    def __str__(self):
        return f"{self.student.full_name} in {self.project.title}"


class ProjectSubmission(models.Model):
    """Abstract text/PDF and video link submitted for an approved project."""

    STATUS_CHOICES = [
        ("not_submitted", "Not Submitted"),
        ("pending_review", "Pending Review"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name="submission"
    )
    abstract_text = models.TextField(blank=True)
    abstract_file = models.FileField(upload_to="abstracts/", blank=True, null=True)
    video_link = models.URLField(
        blank=True, help_text="YouTube, Google Drive, or other video URL"
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="not_submitted"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    pic_remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Submission for {self.project.title} [{self.get_status_display()}]"


class JudgeAssignment(models.Model):
    """Links a judge to a project for evaluation."""

    judge = models.ForeignKey(
        JudgeProfile, on_delete=models.CASCADE, related_name="assignments"
    )
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("judge", "project")

    def __str__(self):
        return f"{self.judge.full_name} → {self.project.title}"


class EvaluationTemplate(models.Model):
    """PIC-controlled rubric and optional downloadable form used by judges."""

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    template_file = models.FileField(upload_to="eval_templates/", blank=True, null=True)
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_eval_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Only one template should be active at a time so judges have a single rubric.
        if self.is_active:
            EvaluationTemplate.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def total_max_score(self):
        total = self.criteria.aggregate(total=models.Sum("max_score"))["total"]
        return total or Decimal("0")

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"


class EvaluationCriterion(models.Model):
    """One scoring criterion within an evaluation template."""

    template = models.ForeignKey(
        EvaluationTemplate, on_delete=models.CASCADE, related_name="criteria"
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    max_score = models.DecimalField(max_digits=6, decimal_places=2)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["order", "id"]

    def clean(self):
        if self.max_score <= 0:
            raise ValidationError(
                {"max_score": "Maximum score must be greater than 0."}
            )

    def __str__(self):
        return f"{self.template.title} — {self.name} ({self.max_score})"


class EvaluationSubmission(models.Model):
    """Judge scoring submission for an assigned project, reviewed by PIC."""

    STATUS_CHOICES = [
        ("pending_review", "Pending Review"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    ]
    assignment = models.OneToOneField(
        JudgeAssignment, on_delete=models.CASCADE, related_name="eval_submission"
    )
    template = models.ForeignKey(
        EvaluationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions",
    )
    completed_form_file = models.FileField(
        upload_to="evaluation_forms/", blank=True, null=True
    )
    remarks = models.TextField(blank=True, help_text="Optional remarks from the judge.")
    total_score = models.DecimalField(
        max_digits=7, decimal_places=2, default=0, editable=False
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default="pending_review"
    )
    submitted_at = models.DateTimeField()
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_eval_submissions",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    pic_feedback = models.TextField(blank=True)

    def recalculate_total(self, commit=True):
        total = self.scores.aggregate(total=models.Sum("score"))["total"] or Decimal(
            "0"
        )
        self.total_score = total
        if commit:
            self.save(update_fields=["total_score"])
        return total

    def __str__(self):
        return (
            f"Evaluation by {self.assignment.judge.full_name} "
            f"for {self.assignment.project.title} [{self.get_status_display()}]"
        )


class EvaluationScore(models.Model):
    """A judge's score for a single active-template criterion."""

    submission = models.ForeignKey(
        EvaluationSubmission, on_delete=models.CASCADE, related_name="scores"
    )
    criterion = models.ForeignKey(
        EvaluationCriterion, on_delete=models.PROTECT, related_name="scores"
    )
    score = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        unique_together = ("submission", "criterion")
        ordering = ["criterion__order", "criterion__id"]

    def clean(self):
        if self.score < 0:
            raise ValidationError({"score": "Score cannot be less than 0."})
        if self.criterion_id and self.score > self.criterion.max_score:
            raise ValidationError(
                {"score": "Score cannot exceed the criterion maximum score."}
            )

    def __str__(self):
        return f"{self.submission} — {self.criterion.name}: {self.score}"


class Deadline(models.Model):
    """
    PIC-configurable deadlines.
    There is one active record per deadline_type; PIC can update it.
    """

    TYPE_CHOICES = [
        ("registration", "Project Registration Deadline"),
        ("submission", "Abstract/Video Submission Deadline"),
        ("evaluation", "Evaluation Deadline"),
    ]
    deadline_type = models.CharField(max_length=20, choices=TYPE_CHOICES, unique=True)
    deadline_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_passed(self):
        """Returns True if the deadline has passed."""
        return timezone.now() > self.deadline_date

    def __str__(self):
        return f"{self.get_deadline_type_display()}: {self.deadline_date.strftime('%d %b %Y %H:%M')}"


class Announcement(models.Model):
    """Public announcements and winner lists published by PIC."""

    title = models.CharField(max_length=255)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    is_winners = models.BooleanField(
        default=False,
        help_text="Mark as True to display on the public winners section.",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="announcements"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        status = "Published" if self.is_published else "Draft"
        return f"[{status}] {self.title}"


class Notification(models.Model):
    """In-app notification stored per user."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="notifications"
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notif → {self.user.username}: {self.message[:60]}"
