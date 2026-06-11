from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone


def role_required(role):
    """
    Decorator that restricts a view to users with a specific role.

    Usage:
        @login_required
        @role_required('student')
        def my_view(request): ...

    Works with roles: 'student', 'judge', 'pic'
    Also allows Django superusers through any role check.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            # Superusers bypass all role checks
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            try:
                user_role = request.user.profile.role
            except Exception:
                messages.error(request, "Your account has no role assigned. Please contact the administrator.")
                return redirect('login')
            if user_role != role:
                messages.error(request, "You do not have permission to access this page.")
                return redirect('home')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def pic_required(view_func):
    """
    Shortcut decorator for PIC-only views.
    Allows both role='pic' users and Django superusers.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        try:
            if request.user.profile.role == 'pic':
                return view_func(request, *args, **kwargs)
        except Exception:
            pass
        messages.error(request, "This area is restricted to PIC/Admin only.")
        return redirect('home')
    return wrapper


def deadline_active(deadline_type, redirect_url='student_dashboard', message=None):
    """
    Decorator that blocks access to a view if the specified deadline has passed
    or if no deadline has been set.

    Args:
        deadline_type: one of 'registration', 'submission', 'evaluation'
        redirect_url: URL name to redirect to if deadline has passed
        message: custom error message (optional)

    Usage:
        @login_required
        @role_required('student')
        @deadline_active('registration')
        def create_project(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # PIC and superusers are never blocked by deadlines
            if request.user.is_authenticated:
                if request.user.is_superuser:
                    return view_func(request, *args, **kwargs)
                try:
                    if request.user.profile.role == 'pic':
                        return view_func(request, *args, **kwargs)
                except Exception:
                    pass
            from evaluation.models import Deadline
            try:
                deadline = Deadline.objects.get(deadline_type=deadline_type, is_active=True)
                if deadline.is_passed():
                    err = message or f"The {deadline.get_deadline_type_display()} has passed."
                    messages.warning(request, err)
                    return redirect(redirect_url)
            except Deadline.DoesNotExist:
                # No deadline set — allow access
                pass
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
