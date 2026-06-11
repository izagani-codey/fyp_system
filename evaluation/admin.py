from django.contrib import admin
from .models import (
    UserProfile, StudentProfile, JudgeProfile,
    Project, ProjectMember, ProjectSubmission,
    JudgeAssignment, Evaluation,
    Deadline, Announcement, Notification,
)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'programme', 'section', 'leader', 'registration_status', 'created_at')
    list_filter = ('registration_status', 'programme')
    search_fields = ('title', 'leader__full_name')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'total_score', 'submitted_at')
    readonly_fields = ('total_score',)


admin.site.register(UserProfile)
admin.site.register(StudentProfile)
admin.site.register(JudgeProfile)
admin.site.register(ProjectMember)
admin.site.register(ProjectSubmission)
admin.site.register(JudgeAssignment)
admin.site.register(Deadline)
admin.site.register(Announcement)
admin.site.register(Notification)
