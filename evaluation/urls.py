from django.urls import path

from evaluation.views.auth_views import (
    about_view,
    dashboard_redirect_view,
    home_view,
    login_view,
    logout_view,
    public_announcements_view,
    register_judge_view,
    register_student_view,
)
from evaluation.views.judge_views import (
    judge_dashboard_view,
    judge_project_detail_view,
    judge_submissions_view,
    submit_evaluation_view,
)
from evaluation.views.pic_views import (
    pic_accept_submission_view,
    pic_announcement_toggle_publish_view,
    pic_announcements_view,
    pic_approve_judge_view,
    pic_approve_project_view,
    pic_assign_judges_view,
    pic_courses_view,
    pic_dashboard_view,
    pic_deadlines_view,
    pic_eval_templates_view,
    pic_evaluations_view,
    pic_export_csv_view,
    pic_generate_top3_announcement_view,
    pic_judge_registrations_view,
    pic_project_registrations_view,
    pic_results_view,
    pic_review_evaluation_view,
    pic_submission_detail_view,
    pic_submissions_view,
    pic_toggle_template_active_view,
)
from evaluation.views.student_views import (
    create_project_view,
    join_project_view,
    student_dashboard_view,
    student_notifications_view,
    submit_project_view,
)

urlpatterns = [
    # ── Public ───────────────────────────────────────────────────────────────
    path("", home_view, name="home"),
    path("about/", about_view, name="about"),
    path("announcements/", public_announcements_view, name="public_announcements"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("register/student/", register_student_view, name="register_student"),
    path("register/judge/", register_judge_view, name="register_judge"),
    path("dashboard/", dashboard_redirect_view, name="dashboard"),
    # ── Student ───────────────────────────────────────────────────────────────
    path("student/dashboard/", student_dashboard_view, name="student_dashboard"),
    path("student/project/create/", create_project_view, name="create_project"),
    path("student/project/join/", join_project_view, name="join_project"),
    path("student/project/submit/", submit_project_view, name="submit_project"),
    path(
        "student/notifications/",
        student_notifications_view,
        name="student_notifications",
    ),
    # ── Judge ─────────────────────────────────────────────────────────────────
    path("judge/dashboard/", judge_dashboard_view, name="judge_dashboard"),
    path(
        "judge/project/<int:assignment_id>/",
        judge_project_detail_view,
        name="judge_project_detail",
    ),
    path(
        "judge/submit/<int:assignment_id>/",
        submit_evaluation_view,
        name="submit_evaluation",
    ),
    path("judge/submissions/", judge_submissions_view, name="judge_submissions"),
    # ── PIC ───────────────────────────────────────────────────────────────────
    path("pic/dashboard/", pic_dashboard_view, name="pic_dashboard"),
    path("pic/courses/", pic_courses_view, name="pic_courses"),
    path(
        "pic/projects/",
        pic_project_registrations_view,
        name="pic_project_registrations",
    ),
    path(
        "pic/projects/<int:project_id>/approve/",
        pic_approve_project_view,
        name="pic_approve_project",
    ),
    path("pic/judges/", pic_judge_registrations_view, name="pic_judge_registrations"),
    path(
        "pic/judges/<int:judge_id>/approve/",
        pic_approve_judge_view,
        name="pic_approve_judge",
    ),
    path("pic/submissions/", pic_submissions_view, name="pic_submissions"),
    path(
        "pic/submissions/<int:project_id>/",
        pic_submission_detail_view,
        name="pic_submission_detail",
    ),
    path(
        "pic/submissions/<int:project_id>/decide/",
        pic_accept_submission_view,
        name="pic_accept_submission",
    ),
    path(
        "pic/assign/<int:project_id>/", pic_assign_judges_view, name="pic_assign_judges"
    ),
    path("pic/evaluations/", pic_evaluations_view, name="pic_evaluations"),
    path(
        "pic/evaluations/<int:submission_id>/review/",
        pic_review_evaluation_view,
        name="pic_review_evaluation",
    ),
    path("pic/eval-templates/", pic_eval_templates_view, name="pic_eval_templates"),
    path(
        "pic/eval-templates/<int:template_id>/toggle/",
        pic_toggle_template_active_view,
        name="pic_toggle_template",
    ),
    path("pic/results/", pic_results_view, name="pic_results"),
    path(
        "pic/results/generate-top3/",
        pic_generate_top3_announcement_view,
        name="pic_generate_top3",
    ),
    path("pic/results/export/", pic_export_csv_view, name="pic_export_csv"),
    path("pic/deadlines/", pic_deadlines_view, name="pic_deadlines"),
    path("pic/announcements/", pic_announcements_view, name="pic_announcements"),
    path(
        "pic/announcements/<int:announcement_id>/publish/",
        pic_announcement_toggle_publish_view,
        name="pic_toggle_publish",
    ),
]
