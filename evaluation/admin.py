from django.contrib import admin

from .models import (
    Announcement,
    Course,
    Deadline,
    EvaluationCriterion,
    EvaluationScore,
    EvaluationSubmission,
    EvaluationTemplate,
    JudgeAssignment,
    JudgeProfile,
    Notification,
    Project,
    ProjectMember,
    ProjectSubmission,
    StudentProfile,
    UserProfile,
)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "section",
        "leader",
        "registration_status",
        "created_at",
    )
    list_filter = ("registration_status", "course")
    search_fields = ("title", "leader__full_name")


class EvaluationCriterionInline(admin.TabularInline):
    model = EvaluationCriterion
    extra = 1


@admin.register(EvaluationTemplate)
class EvaluationTemplateAdmin(admin.ModelAdmin):
    list_display = ("title", "is_active", "created_by", "created_at")
    list_filter = ("is_active",)
    inlines = [EvaluationCriterionInline]


class EvaluationScoreInline(admin.TabularInline):
    model = EvaluationScore
    extra = 0
    readonly_fields = ("criterion", "score")
    can_delete = False


@admin.register(EvaluationSubmission)
class EvaluationSubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "assignment",
        "template",
        "total_score",
        "status",
        "submitted_at",
        "reviewed_by",
        "reviewed_at",
    )
    list_filter = ("status", "template")
    inlines = [EvaluationScoreInline]


admin.site.register(UserProfile)
admin.site.register(StudentProfile)
admin.site.register(JudgeProfile)
admin.site.register(ProjectMember)
admin.site.register(ProjectSubmission)
admin.site.register(JudgeAssignment)
admin.site.register(Deadline)
admin.site.register(Announcement)
admin.site.register(Notification)
