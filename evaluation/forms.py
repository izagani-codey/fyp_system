from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from evaluation.models import (
    Announcement,
    Course,
    Deadline,
    EvaluationCriterion,
    EvaluationScore,
    EvaluationSubmission,
    EvaluationTemplate,
    JudgeProfile,
    Project,
    ProjectSubmission,
    StudentProfile,
)

# ── Registration forms ────────────────────────────────────────────────────────


class StudentRegistrationForm(forms.Form):
    """Public registration form for students. Creates User + UserProfile + StudentProfile."""

    username = forms.CharField(max_length=150, label="Username")
    email = forms.EmailField(label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, label="Confirm Password"
    )
    full_name = forms.CharField(max_length=150, label="Full Name")
    student_id = forms.CharField(max_length=20, label="Student ID")
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        label="Course",
        empty_label="Select your course",
    )
    programme = forms.CharField(
        max_length=100,
        required=False,
        label="Programme (optional)",
        help_text="Optional legacy programme name, if different from your course.",
    )
    section = forms.CharField(max_length=50, label="Section / Group")
    phone_number = forms.CharField(max_length=20, label="Phone Number")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.filter(is_active=True).order_by(
            "name"
        )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_student_id(self):
        sid = self.cleaned_data.get("student_id")
        if StudentProfile.objects.filter(student_id=sid).exists():
            raise forms.ValidationError("This Student ID is already registered.")
        return sid


class JudgeRegistrationForm(forms.Form):
    """Public registration form for judges. Creates User + UserProfile + JudgeProfile."""

    username = forms.CharField(max_length=150, label="Username")
    email = forms.EmailField(label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(
        widget=forms.PasswordInput, label="Confirm Password"
    )
    full_name = forms.CharField(max_length=150, label="Full Name")
    department = forms.CharField(max_length=100, label="Department")
    expertise_area = forms.CharField(
        max_length=200,
        label="Expertise Area",
        widget=forms.TextInput(
            attrs={"placeholder": "e.g. Machine Learning, Web Development"}
        ),
    )
    phone_number = forms.CharField(max_length=20, label="Phone Number")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


# ── Project forms ─────────────────────────────────────────────────────────────


class ProjectCreateForm(forms.ModelForm):
    """
    Form for a student to register a new project.
    The 'leader' field is set programmatically in the view (not shown in form).
    """

    class Meta:
        model = Project
        fields = ["title", "course", "programme", "section", "supervisor_name"]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "Enter your full project title"}
            ),
            "programme": forms.TextInput(
                attrs={"placeholder": "Optional legacy programme name"}
            ),
            "section": forms.TextInput(attrs={"placeholder": "e.g. CS2A, IT3B"}),
            "supervisor_name": forms.TextInput(
                attrs={"placeholder": "Full name of your supervisor"}
            ),
        }
        labels = {
            "title": "Project Title",
            "course": "Course",
            "programme": "Programme (optional)",
            "section": "Section / Group",
            "supervisor_name": "Supervisor Name",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["course"].queryset = Course.objects.filter(is_active=True).order_by(
            "name"
        )
        self.fields["course"].empty_label = "Select project course"


class ProjectJoinForm(forms.Form):
    """
    Form for a student to join an existing project by entering the project's ID.
    The project must be in 'pending' or 'approved' status.
    """

    project_id = forms.IntegerField(
        label="Project ID",
        help_text="Ask your project leader for the Project ID shown on their dashboard.",
    )

    def clean_project_id(self):
        pid = self.cleaned_data.get("project_id")
        try:
            project = Project.objects.get(pk=pid)
        except Project.DoesNotExist:
            raise forms.ValidationError("No project found with this ID.")
        if project.registration_status == "rejected":
            raise forms.ValidationError(
                "This project has been rejected and cannot accept new members."
            )
        return pid


# ── Submission form ───────────────────────────────────────────────────────────


class ProjectSubmissionForm(forms.ModelForm):
    """
    Form for a student (project leader) to submit abstract and video link.
    At least one of abstract_text or abstract_file must be provided.
    """

    class Meta:
        model = ProjectSubmission
        fields = ["abstract_text", "abstract_file", "video_link"]
        widgets = {
            "abstract_text": forms.Textarea(
                attrs={
                    "rows": 8,
                    "placeholder": "Type or paste your project abstract here...",
                }
            ),
            "video_link": forms.URLInput(
                attrs={
                    "placeholder": "https://www.youtube.com/watch?v=... or Google Drive link"
                }
            ),
        }
        labels = {
            "abstract_text": "Abstract Text",
            "abstract_file": "Abstract PDF / Word File (optional if text provided)",
            "video_link": "Video Presentation Link (YouTube / Google Drive)",
        }

    def clean(self):
        cleaned = super().clean()
        text = cleaned.get("abstract_text", "").strip()
        file = cleaned.get("abstract_file")
        if not text and not file:
            raise forms.ValidationError(
                "Please provide either an abstract text or upload an abstract file (or both)."
            )
        return cleaned


# ── Evaluation forms ──────────────────────────────────────────────────────────


class EvaluationSubmissionForm(forms.ModelForm):
    """Judge submits criterion scores, optional completed form file, and remarks."""

    class Meta:
        model = EvaluationSubmission
        fields = ["completed_form_file", "remarks"]
        widgets = {
            "remarks": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Optional: add any notes or remarks for the PIC...",
                }
            ),
        }
        labels = {
            "completed_form_file": "Completed Evaluation Form (optional evidence)",
            "remarks": "Remarks (optional)",
        }

    def __init__(self, template, *args, **kwargs):
        self.template = template
        self.criteria = list(template.criteria.all()) if template else []
        self.score_field_names = []
        super().__init__(*args, **kwargs)

        existing_scores = {}
        if self.instance and self.instance.pk:
            existing_scores = {
                score.criterion_id: score.score
                for score in self.instance.scores.select_related("criterion")
            }

        for criterion in self.criteria:
            field_name = f"criterion_{criterion.id}"
            self.score_field_names.append(field_name)
            self.fields[field_name] = forms.DecimalField(
                min_value=Decimal("0"),
                max_value=criterion.max_score,
                decimal_places=2,
                label=f"{criterion.name} (max {criterion.max_score})",
                initial=existing_scores.get(criterion.id),
                help_text=criterion.description,
            )

    def clean(self):
        cleaned = super().clean()
        if not self.template:
            raise forms.ValidationError("No active evaluation template is available.")
        if not self.criteria:
            raise forms.ValidationError(
                "The active evaluation template has no criteria yet."
            )
        return cleaned

    def score_items(self):
        """Return validated (criterion, score) pairs for saving in the view."""
        items = []
        for criterion in self.criteria:
            score = self.cleaned_data.get(f"criterion_{criterion.id}")
            items.append((criterion, score))
        return items


class EvaluationReviewForm(forms.Form):
    """PIC accepts or rejects a submitted evaluation, with optional feedback."""

    action = forms.ChoiceField(
        choices=[("accept", "Accept"), ("reject", "Reject")],
        widget=forms.HiddenInput,
    )
    pic_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Optional feedback for the judge (required if rejecting)...",
            }
        ),
        label="PIC Feedback",
    )

    def clean(self):
        cleaned = super().clean()
        if (
            cleaned.get("action") == "reject"
            and not cleaned.get("pic_feedback", "").strip()
        ):
            raise forms.ValidationError(
                "Please provide feedback explaining why the submission is being rejected."
            )
        return cleaned


class EvaluationTemplateForm(forms.ModelForm):
    """PIC creates a dynamic evaluation template and optional downloadable file."""

    class Meta:
        model = EvaluationTemplate
        fields = ["title", "description", "template_file", "is_active"]
        widgets = {
            "title": forms.TextInput(
                attrs={"placeholder": "e.g. FYP Evaluation Rubric Semester 2 2026"}
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Brief description of this template...",
                }
            ),
        }
        labels = {
            "title": "Template Title",
            "description": "Description (optional)",
            "template_file": "Template File (optional PDF / Word / Excel)",
            "is_active": "Make this the active template",
        }


class EvaluationCriterionForm(forms.ModelForm):
    """PIC adds or edits one scoring criterion."""

    class Meta:
        model = EvaluationCriterion
        fields = ["name", "description", "max_score", "order"]
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 2, "placeholder": "Short marking guide"}
            ),
            "order": forms.NumberInput(attrs={"min": 1}),
            "max_score": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }


# ── PIC admin forms ───────────────────────────────────────────────────────────


class DeadlineForm(forms.ModelForm):
    """Form for PIC to set or update a deadline."""

    deadline_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
        label="Deadline Date & Time",
    )

    class Meta:
        model = Deadline
        fields = ["deadline_type", "deadline_date", "is_active"]
        labels = {
            "deadline_type": "Deadline Type",
            "is_active": "Active (enforced)",
        }

    def clean_deadline_date(self):
        dt = self.cleaned_data.get("deadline_date")
        if dt and dt <= timezone.now():
            raise forms.ValidationError("Deadline must be in the future.")
        return dt


class AnnouncementForm(forms.ModelForm):
    """Form for PIC to create or edit an announcement."""

    class Meta:
        model = Announcement
        fields = ["title", "content", "is_winners", "is_published"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "Announcement title"}),
            "content": forms.Textarea(
                attrs={
                    "rows": 8,
                    "placeholder": "Write the announcement content here...",
                }
            ),
        }
        labels = {
            "is_winners": "Mark as Winner Announcement",
            "is_published": "Publish immediately",
        }


class CourseForm(forms.ModelForm):
    """Form for PIC to create or edit courses."""

    class Meta:
        model = Course
        fields = ["name", "code", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={"placeholder": "e.g. Bachelor of Computer Science"}
            ),
            "code": forms.TextInput(
                attrs={"placeholder": "e.g. CS, IT, SE"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Brief course description..."}
            ),
        }
        labels = {
            "is_active": "Active (visible in registration forms)",
        }
