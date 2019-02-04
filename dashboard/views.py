from django.shortcuts import render
from django.http import HttpResponseForbidden

from analysis.models import Issue, AnalysisProject, Warning


def dashboard_index(request):
    user = request.user
    if user.is_staff:

        # get the current analyses that have been created.  We would like to view their status
        analysis_projects = AnalysisProject.objects.filter(completed=False)

        # show any errors in submitted jobs
        job_query_warnings = Warning.objects.all()

        # Show any other issues that might have occurred:
        other_issues = Issue.objects.all()

        # allow us to check the status of the cromwell server

        context = {}
        context['projects'] = analysis_projects
        context['warnings'] = job_query_warnings
        context['issues'] = other_issues

        return render(request, 'dashboard/dashboard_home.html', context)
    else:
        return HttpResponseForbidden()