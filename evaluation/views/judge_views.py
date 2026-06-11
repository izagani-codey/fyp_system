from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from evaluation.decorators import role_required

@login_required
@role_required('judge')
def judge_dashboard_view(request):
    return render(request, 'evaluation/judge/dashboard.html', {})

@login_required
@role_required('judge')
def judge_project_detail_view(request, assignment_id):
    return render(request, 'evaluation/judge/project_detail.html', {})

@login_required
@role_required('judge')
def evaluate_view(request, assignment_id):
    return render(request, 'evaluation/judge/evaluate.html', {})

@login_required
@role_required('judge')
def completed_evaluations_view(request):
    return render(request, 'evaluation/judge/completed_evaluations.html', {})
