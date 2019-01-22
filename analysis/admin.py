from django.contrib import admin

from .models import Workflow, AnalysisProject, SubmittedJob

class WorkflowAdmin(admin.ModelAdmin):
    list_display = ('workflow_name', 'workflow_id', 'version_id', 'is_default', 'is_active', 'workflow_title', 'workflow_short_description', 'workflow_long_description')
    list_editable = ('is_default', 'is_active', 'workflow_title', 'workflow_short_description')
    list_display_links = ('workflow_name',)


class AnalysisProjectAdmin(admin.ModelAdmin):
    list_display = ('analysis_uuid', 'owner', 'started', 'completed')
    list_editable = ()
    list_display_links = ('analysis_uuid',)


class SubmittedJobAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'job_status', 'job_staging_dir')
    list_editable = ()
    list_display_links = ('job_id',)

admin.site.register(Workflow, WorkflowAdmin)
admin.site.register(AnalysisProject, AnalysisProjectAdmin)
admin.site.register(SubmittedJob, SubmittedJobAdmin)
