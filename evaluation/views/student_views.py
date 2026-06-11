from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from evaluation.decorators import role_required

@login_required
@role_required('student')
def student_dashboard_view(request):
    return render(request, 'evaluation/student/dashboard.html', {})

@login_required
@role_required('student')
def create_project_view(request):
    return render(request, 'evaluation/student/create_project.html', {})

@login_required
@role_required('student')
def join_project_view(request):
    return render(request, 'evaluation/student/join_project.html', {})

@login_required
@role_required('student')
def submit_project_view(request):
    return render(request, 'evaluation/student/submit_project.html', {})

@login_required
@role_required('student')
def student_notifications_view(request):
    return render(request, 'evaluation/student/notifications.html', {})
