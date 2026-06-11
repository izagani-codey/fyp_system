from django.shortcuts import render, redirect
from evaluation.decorators import pic_required

@pic_required
def pic_dashboard_view(request):
    return render(request, 'evaluation/pic/dashboard.html', {})

@pic_required
def pic_project_registrations_view(request):
    return render(request, 'evaluation/pic/project_registrations.html', {})

@pic_required
def pic_approve_project_view(request, project_id):
    return redirect('pic_project_registrations')

@pic_required
def pic_judge_registrations_view(request):
    return render(request, 'evaluation/pic/judge_registrations.html', {})

@pic_required
def pic_approve_judge_view(request, judge_id):
    return redirect('pic_judge_registrations')

@pic_required
def pic_submissions_view(request):
    return render(request, 'evaluation/pic/submissions.html', {})

@pic_required
def pic_submission_detail_view(request, project_id):
    return render(request, 'evaluation/pic/submission_detail.html', {})

@pic_required
def pic_accept_submission_view(request, project_id):
    return redirect('pic_submissions')

@pic_required
def pic_assign_judges_view(request, project_id):
    return render(request, 'evaluation/pic/assign_judges.html', {})

@pic_required
def pic_evaluations_view(request):
    return render(request, 'evaluation/pic/evaluations.html', {})

@pic_required
def pic_results_view(request):
    return render(request, 'evaluation/pic/results.html', {})

@pic_required
def pic_export_csv_view(request):
    from evaluation.utils import export_results_csv
    return export_results_csv()

@pic_required
def pic_deadlines_view(request):
    return render(request, 'evaluation/pic/deadlines.html', {})

@pic_required
def pic_announcements_view(request):
    return render(request, 'evaluation/pic/announcements.html', {})

@pic_required
def pic_announcement_toggle_publish_view(request, announcement_id):
    return redirect('pic_announcements')
