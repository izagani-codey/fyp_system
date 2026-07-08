from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from evaluation.forms import JudgeRegistrationForm, StudentRegistrationForm
from evaluation.models import Announcement, JudgeProfile, StudentProfile, UserProfile
from evaluation.utils import notify


def home_view(request):
    """Public landing page — conference style."""
    # Show only published announcements (latest 3 on homepage)
    recent_announcements = Announcement.objects.filter(is_published=True).order_by(
        "-published_at"
    )[:3]
    return render(
        request, "evaluation/home.html", {"recent_announcements": recent_announcements}
    )


def about_view(request):
    """Static about/process page."""
    return render(request, "evaluation/about.html")


def public_announcements_view(request):
    """
    Public page showing all published announcements.
    Winners are highlighted if announcement.is_winners is True.
    """
    announcements = Announcement.objects.filter(is_published=True).order_by(
        "-published_at"
    )
    winners = announcements.filter(is_winners=True)
    general = announcements.filter(is_winners=False)
    return render(
        request,
        "evaluation/announcements.html",
        {
            "announcements": announcements,
            "winners": winners,
            "general": general,
        },
    )


def login_view(request):
    """Handles login for all roles; redirects to role-appropriate dashboard."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return _redirect_by_role(user)
        messages.error(request, "Invalid username or password. Please try again.")

    return render(request, "evaluation/auth/login.html")


def logout_view(request):
    """Logs out and redirects to home."""
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


def register_student_view(request):
    """
    Public student registration.
    Creates: User, UserProfile(role='student'), StudentProfile.
    """
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            # Create Django User
            user = User.objects.create_user(
                username=d["username"],
                email=d["email"],
                password=d["password"],
            )
            # Assign role
            UserProfile.objects.create(user=user, role="student")
            # Create student profile
            StudentProfile.objects.create(
                user=user,
                student_id=d["student_id"],
                full_name=d["full_name"],
                course=d["course"],
                programme=d["programme"] or d["course"].name,
                section=d["section"],
                phone_number=d["phone_number"],
            )
            # Notify student
            notify(
                user,
                "Welcome! Your student account has been created. You can now register a project.",
                email_subject="FYP System — Registration Successful",
            )
            messages.success(request, "Account created successfully! Please log in.")
            return redirect("login")
    else:
        form = StudentRegistrationForm()

    return render(request, "evaluation/auth/register_student.html", {"form": form})


def register_judge_view(request):
    """
    Public judge registration.
    Creates: User, UserProfile(role='judge'), JudgeProfile(status='pending').
    """
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == "POST":
        form = JudgeRegistrationForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            user = User.objects.create_user(
                username=d["username"],
                email=d["email"],
                password=d["password"],
            )
            UserProfile.objects.create(user=user, role="judge")
            JudgeProfile.objects.create(
                user=user,
                full_name=d["full_name"],
                department=d["department"],
                expertise_area=d["expertise_area"],
                phone_number=d["phone_number"],
            )
            notify(
                user,
                "Your judge registration has been submitted and is pending PIC approval.",
                email_subject="FYP System — Judge Registration Received",
            )
            messages.success(request, "Registration submitted! Awaiting PIC approval.")
            return redirect("login")
    else:
        form = JudgeRegistrationForm()

    return render(request, "evaluation/auth/register_judge.html", {"form": form})


def dashboard_redirect_view(request):
    """
    Generic /dashboard/ that redirects to the correct role dashboard.
    login_required is handled by LOGIN_URL setting.
    """
    if not request.user.is_authenticated:
        return redirect("login")
    return _redirect_by_role(request.user)


def _redirect_by_role(user):
    """Internal helper — returns HttpResponseRedirect based on user role."""
    if user.is_superuser:
        return redirect("pic_dashboard")
    try:
        role = user.profile.role
    except Exception:
        return redirect("home")
    if role == "student":
        return redirect("student_dashboard")
    elif role == "judge":
        return redirect("judge_dashboard")
    elif role == "pic":
        return redirect("pic_dashboard")
    return redirect("home")
