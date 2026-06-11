import csv
from django.core.mail import send_mail
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from evaluation.models import Notification, Evaluation, Project


def notify(user, message, email_subject=None, email_body=None):
    """
    Create an in-app notification and send an email.

    Args:
        user: Django User object
        message: notification message (used for both DB record and email body if not specified)
        email_subject: optional custom email subject
        email_body: optional custom email body (defaults to message)

    During development, emails are printed to the console (EMAIL_BACKEND = console).
    """
    # Always create in-app notification
    Notification.objects.create(user=user, message=message)

    # Send email notification (goes to console in development)
    subject = email_subject or "FYP Evaluation System — Notification"
    body = email_body or message
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,  # Never let email failure crash the app
        )
    except Exception:
        pass


def export_results_csv(response_or_filename=None):
    """
    Generate a CSV of all evaluation results.

    Returns an HttpResponse with Content-Disposition: attachment for CSV download.

    CSV columns:
    Project ID, Project Title, Programme, Section, Supervisor,
    Leader Name, Leader Student ID,
    Judge Name, Judge Department,
    Abstract Quality (/10), Problem Statement (/15),
    System Functionality (/25), Technical Implementation (/20),
    Presentation Quality (/15), Innovation & Value (/10),
    Total Score (/95), Comments, Submitted At
    """
    response = HttpResponse(content_type='text/csv')
    filename = f"fyp_results_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)

    # Header row
    writer.writerow([
        'Project ID', 'Project Title', 'Programme', 'Section', 'Supervisor',
        'Leader Name', 'Leader Student ID',
        'Judge Name', 'Judge Department',
        'Abstract Quality (/10)', 'Problem Statement (/15)',
        'System Functionality (/25)', 'Technical Implementation (/20)',
        'Presentation Quality (/15)', 'Innovation & Value (/10)',
        'Total Score (/95)', 'Comments', 'Submitted At',
    ])

    # Fetch all evaluations with related data
    evaluations = Evaluation.objects.select_related(
        'assignment__project__leader',
        'assignment__judge',
    ).order_by('assignment__project__title', 'assignment__judge__full_name')

    for ev in evaluations:
        project = ev.assignment.project
        judge = ev.assignment.judge
        writer.writerow([
            project.id,
            project.title,
            project.programme,
            project.section,
            project.supervisor_name,
            project.leader.full_name,
            project.leader.student_id,
            judge.full_name,
            judge.department,
            ev.abstract_quality,
            ev.problem_statement,
            ev.system_functionality,
            ev.technical_implementation,
            ev.presentation_quality,
            ev.innovation_value,
            ev.total_score,
            ev.overall_comments,
            ev.submitted_at.strftime('%Y-%m-%d %H:%M') if ev.submitted_at else '',
        ])

    return response


def get_project_average_score(project):
    """
    Return the average total_score across all submitted evaluations for a project.
    Returns None if no evaluations exist yet.
    """
    evaluations = Evaluation.objects.filter(assignment__project=project)
    if not evaluations.exists():
        return None
    total = sum(e.total_score for e in evaluations)
    return round(total / evaluations.count(), 2)
