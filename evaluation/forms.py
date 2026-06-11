from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from evaluation.models import (
    StudentProfile, JudgeProfile, Project, ProjectSubmission,
    Evaluation, Deadline, Announcement,
)


# ── Registration forms ────────────────────────────────────────────────────────

class StudentRegistrationForm(forms.Form):
    """Public registration form for students. Creates User + UserProfile + StudentProfile."""
    username = forms.CharField(max_length=150, label="Username")
    email = forms.EmailField(label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    full_name = forms.CharField(max_length=150, label="Full Name")
    student_id = forms.CharField(max_length=20, label="Student ID")
    programme = forms.CharField(max_length=100, label="Programme")
    section = forms.CharField(max_length=50, label="Section / Group")
    phone_number = forms.CharField(max_length=20, label="Phone Number")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('confirm_password'):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_student_id(self):
        sid = self.cleaned_data.get('student_id')
        if StudentProfile.objects.filter(student_id=sid).exists():
            raise forms.ValidationError("This Student ID is already registered.")
        return sid


class JudgeRegistrationForm(forms.Form):
    """Public registration form for judges. Creates User + UserProfile + JudgeProfile."""
    username = forms.CharField(max_length=150, label="Username")
    email = forms.EmailField(label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    full_name = forms.CharField(max_length=150, label="Full Name")
    department = forms.CharField(max_length=100, label="Department")
    expertise_area = forms.CharField(
        max_length=200, label="Expertise Area",
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Machine Learning, Web Development'})
    )
    phone_number = forms.CharField(max_length=20, label="Phone Number")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('confirm_password'):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
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
        fields = ['title', 'programme', 'section', 'supervisor_name']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Enter your full project title'}),
            'programme': forms.TextInput(attrs={'placeholder': 'e.g. Bachelor of Computer Science'}),
            'section': forms.TextInput(attrs={'placeholder': 'e.g. CS2A, IT3B'}),
            'supervisor_name': forms.TextInput(attrs={'placeholder': 'Full name of your supervisor'}),
        }
        labels = {
            'title': 'Project Title',
            'programme': 'Programme',
            'section': 'Section / Group',
            'supervisor_name': 'Supervisor Name',
        }


class ProjectJoinForm(forms.Form):
    """
    Form for a student to join an existing project by entering the project's ID.
    The project must be in 'pending' or 'approved' status.
    """
    project_id = forms.IntegerField(
        label="Project ID",
        help_text="Ask your project leader for the Project ID shown on their dashboard."
    )

    def clean_project_id(self):
        pid = self.cleaned_data.get('project_id')
        try:
            project = Project.objects.get(pk=pid)
        except Project.DoesNotExist:
            raise forms.ValidationError("No project found with this ID.")
        if project.registration_status == 'rejected':
            raise forms.ValidationError("This project has been rejected and cannot accept new members.")
        return pid


# ── Submission form ───────────────────────────────────────────────────────────

class ProjectSubmissionForm(forms.ModelForm):
    """
    Form for a student (project leader) to submit abstract and video link.
    At least one of abstract_text or abstract_file must be provided.
    """
    class Meta:
        model = ProjectSubmission
        fields = ['abstract_text', 'abstract_file', 'video_link']
        widgets = {
            'abstract_text': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Type or paste your project abstract here...'
            }),
            'video_link': forms.URLInput(attrs={
                'placeholder': 'https://www.youtube.com/watch?v=... or Google Drive link'
            }),
        }
        labels = {
            'abstract_text': 'Abstract Text',
            'abstract_file': 'Abstract PDF / Word File (optional if text provided)',
            'video_link': 'Video Presentation Link (YouTube / Google Drive)',
        }

    def clean(self):
        cleaned = super().clean()
        text = cleaned.get('abstract_text', '').strip()
        file = cleaned.get('abstract_file')
        if not text and not file:
            raise forms.ValidationError(
                "Please provide either an abstract text or upload an abstract file (or both)."
            )
        return cleaned


# ── Evaluation form ───────────────────────────────────────────────────────────

class EvaluationForm(forms.ModelForm):
    """
    Score form for judges. Total score is auto-calculated in Evaluation.save().
    Each field has a help_text showing the maximum marks.
    """
    class Meta:
        model = Evaluation
        fields = [
            'abstract_quality',
            'problem_statement',
            'system_functionality',
            'technical_implementation',
            'presentation_quality',
            'innovation_value',
            'overall_comments',
        ]
        widgets = {
            'abstract_quality':         forms.NumberInput(attrs={'min': 0, 'max': 10}),
            'problem_statement':        forms.NumberInput(attrs={'min': 0, 'max': 15}),
            'system_functionality':     forms.NumberInput(attrs={'min': 0, 'max': 25}),
            'technical_implementation': forms.NumberInput(attrs={'min': 0, 'max': 20}),
            'presentation_quality':     forms.NumberInput(attrs={'min': 0, 'max': 15}),
            'innovation_value':         forms.NumberInput(attrs={'min': 0, 'max': 10}),
            'overall_comments':         forms.Textarea(attrs={'rows': 4, 'placeholder': 'Optional overall feedback...'}),
        }
        labels = {
            'abstract_quality':         'Abstract Quality',
            'problem_statement':        'Problem Statement Clarity',
            'system_functionality':     'System Functionality',
            'technical_implementation': 'Technical Implementation',
            'presentation_quality':     'Presentation / Video Quality',
            'innovation_value':         'Innovation & Value',
            'overall_comments':         'Overall Comments',
        }
        help_texts = {
            'abstract_quality':         'Max: 10 marks',
            'problem_statement':        'Max: 15 marks',
            'system_functionality':     'Max: 25 marks',
            'technical_implementation': 'Max: 20 marks',
            'presentation_quality':     'Max: 15 marks',
            'innovation_value':         'Max: 10 marks',
        }

    def clean_abstract_quality(self):
        val = self.cleaned_data.get('abstract_quality', 0)
        if not (0 <= val <= 10):
            raise forms.ValidationError("Must be between 0 and 10.")
        return val

    def clean_problem_statement(self):
        val = self.cleaned_data.get('problem_statement', 0)
        if not (0 <= val <= 15):
            raise forms.ValidationError("Must be between 0 and 15.")
        return val

    def clean_system_functionality(self):
        val = self.cleaned_data.get('system_functionality', 0)
        if not (0 <= val <= 25):
            raise forms.ValidationError("Must be between 0 and 25.")
        return val

    def clean_technical_implementation(self):
        val = self.cleaned_data.get('technical_implementation', 0)
        if not (0 <= val <= 20):
            raise forms.ValidationError("Must be between 0 and 20.")
        return val

    def clean_presentation_quality(self):
        val = self.cleaned_data.get('presentation_quality', 0)
        if not (0 <= val <= 15):
            raise forms.ValidationError("Must be between 0 and 15.")
        return val

    def clean_innovation_value(self):
        val = self.cleaned_data.get('innovation_value', 0)
        if not (0 <= val <= 10):
            raise forms.ValidationError("Must be between 0 and 10.")
        return val


# ── PIC admin forms ───────────────────────────────────────────────────────────

class DeadlineForm(forms.ModelForm):
    """Form for PIC to set or update a deadline."""
    deadline_date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        input_formats=['%Y-%m-%dT%H:%M'],
        label="Deadline Date & Time",
    )

    class Meta:
        model = Deadline
        fields = ['deadline_type', 'deadline_date', 'is_active']
        labels = {
            'deadline_type': 'Deadline Type',
            'is_active': 'Active (enforced)',
        }

    def clean_deadline_date(self):
        dt = self.cleaned_data.get('deadline_date')
        if dt and dt <= timezone.now():
            raise forms.ValidationError("Deadline must be in the future.")
        return dt


class AnnouncementForm(forms.ModelForm):
    """Form for PIC to create or edit an announcement."""
    class Meta:
        model = Announcement
        fields = ['title', 'content', 'is_winners', 'is_published']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Announcement title'}),
            'content': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Write the announcement content here...'
            }),
        }
        labels = {
            'is_winners': 'Mark as Winner Announcement',
            'is_published': 'Publish immediately',
        }
