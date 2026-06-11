from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """Extends Django's built-in User with a role."""
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('judge', 'Judge'),
        ('pic', 'PIC'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class StudentProfile(models.Model):
    """Extra data for a student user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    student_id = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    programme = models.CharField(max_length=100)
    section = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"


class JudgeProfile(models.Model):
    """Extra data for a judge user."""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='judge_profile')
    full_name = models.CharField(max_length=150)
    department = models.CharField(max_length=100)
    expertise_area = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=20)
    registration_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.department})"


class Project(models.Model):
    """
    A FYP project/group — the main evaluation unit.
    One or more students belong to a project.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    title = models.CharField(max_length=255)
    programme = models.CharField(max_length=100)
    section = models.CharField(max_length=50)
    supervisor_name = models.CharField(max_length=150)
    # The student who created the project and acts as leader
    leader = models.ForeignKey(
        'StudentProfile',
        on_delete=models.CASCADE,
        related_name='led_projects'
    )
    registration_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    pic_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} [{self.get_registration_status_display()}]"


class ProjectMember(models.Model):
    """Links additional student members to a project (the leader is tracked on Project.leader)."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='members')
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='memberships')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'student')

    def __str__(self):
        return f"{self.student.full_name} in {self.project.title}"


class ProjectSubmission(models.Model):
    """Abstract text/PDF and video link submitted for an approved project."""
    STATUS_CHOICES = [
        ('not_submitted', 'Not Submitted'),
        ('pending_review', 'Pending Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='submission')
    abstract_text = models.TextField(blank=True)
    abstract_file = models.FileField(upload_to='abstracts/', blank=True, null=True)
    video_link = models.URLField(blank=True, help_text='YouTube, Google Drive, or other video URL')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_submitted')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    pic_remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Submission for {self.project.title} [{self.get_status_display()}]"


class JudgeAssignment(models.Model):
    """Links a judge to a project for evaluation."""
    judge = models.ForeignKey(JudgeProfile, on_delete=models.CASCADE, related_name='assignments')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('judge', 'project')

    def __str__(self):
        return f"{self.judge.full_name} → {self.project.title}"


class Evaluation(models.Model):
    """Score sheet submitted by a judge for their assigned project."""
    assignment = models.OneToOneField(
        JudgeAssignment, on_delete=models.CASCADE, related_name='evaluation'
    )
    # Criteria and max marks
    abstract_quality = models.PositiveSmallIntegerField(default=0)        # max 10
    problem_statement = models.PositiveSmallIntegerField(default=0)       # max 15
    system_functionality = models.PositiveSmallIntegerField(default=0)    # max 25
    technical_implementation = models.PositiveSmallIntegerField(default=0) # max 20
    presentation_quality = models.PositiveSmallIntegerField(default=0)    # max 15
    innovation_value = models.PositiveSmallIntegerField(default=0)        # max 10
    overall_comments = models.TextField(blank=True)
    total_score = models.PositiveSmallIntegerField(default=0, editable=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Auto-calculate total from six criteria on every save
        self.total_score = (
            self.abstract_quality
            + self.problem_statement
            + self.system_functionality
            + self.technical_implementation
            + self.presentation_quality
            + self.innovation_value
        )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Eval by {self.assignment.judge.full_name} for {self.assignment.project.title} — {self.total_score}/95"


class Deadline(models.Model):
    """
    PIC-configurable deadlines.
    There is one active record per deadline_type; PIC can update it.
    """
    TYPE_CHOICES = [
        ('registration', 'Project Registration Deadline'),
        ('submission', 'Abstract/Video Submission Deadline'),
        ('evaluation', 'Evaluation Deadline'),
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
        help_text='Mark as True to display on the public winners section.'
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='announcements'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = "Published" if self.is_published else "Draft"
        return f"[{status}] {self.title}"


class Notification(models.Model):
    """In-app notification stored per user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notif → {self.user.username}: {self.message[:60]}"
