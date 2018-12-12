import os
import json

from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseBadRequest
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.urls import reverse

from .models import Workflow
from .view_utils import get_workflow, \
    validate_workflow_dir, \
    fill_context, \
    fill_wdl_input


def home(request):
    return render(request, 'analysis/home.html', {'msg': 'hello'})


class AnalysisView(View):

    # enforces that this view is protected by login:
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @staticmethod
    def get_url_params(kwargs):
        '''
        The kwargs dict carries the URL parameters.
        We expect at least a `workflow_id`.  An optional
        `version_id` can also be provided.  If not, it is set to None
        '''
        workflow_id = kwargs['workflow_id']
        try:
            version_id = kwargs['version_id']
        except KeyError:
            version_id = None
        return (workflow_id, version_id)


    def get(self, request, *args, **kwargs):
        '''
        When the url is requested using the GET method, we display the form.

        Depending on the implementation of the workflow, this could require 
        dynamic content to be loaded from the database.  Hence, we need to 
        look at the workflow details to determine if any such details are needed.
        '''

        # Get the workflow and possibly version id from the request params:
        workflow_id, version_id = AnalysisView.get_url_params(kwargs)
        
        # get the workflow object based on the workflow ID/version
        try:
            workflow_obj = get_workflow(workflow_id, version_id, request.user.is_staff)
        except Exception:
            return HttpResponseBadRequest('Error when querying for workflow.')

        # if we are here, we have a workflow object from the database.
        # We can use that to find the appropriate workflow directory where
        # everything lives.
        workflow_dir = workflow_obj.workflow_location
        template = os.path.join(workflow_dir, settings.HTML_TEMPLATE_NAME)

        # prepare and empty context which we will fill-in
        context_dict = {}

        # now that we have a valid workflow directory,
        # we look at the GUI spec and load the 'handlers' for each input 
        # element.  These are snippets of python code that specify how
        # dynamic, database-driven data is queried for the UI.
        fill_context(request, workflow_obj, context_dict)

        # add some additional elements to the form:
        # Need to link the javascript for the page
        context_dict['form_javascript'] = os.path.join(settings.STATIC_URL, 
            workflow_dir, 
            settings.FORM_JAVASCRIPT_NAME)
        # the url so the POST goes to the correct URL
        context_dict['submit_url'] = reverse('workflow_version_view', 
            kwargs={'workflow_id': workflow_id, 'version_id': version_id}
        )

        return render(request, template, context_dict)


    def post(self, request, *args, **kwargs):
        '''
        With a POST request, the form is being submitted.  We parse the contents
        of that request, prepare a pending analysis, and prepare a summary.
        '''
        # Get the workflow and possibly version id from the request params:
        workflow_id, version_id = AnalysisView.get_url_params(kwargs)

        # parse the payload from the POST request and make a dictionary
        data = request.POST.get('data')
        j = json.loads(data)

        # add the url params so we know which workflow to use.  Add to the overall
        # dict containing the data
        j['workflow_id'] = workflow_id
        j['version_id'] = version_id

        # Fill out the template for the WDL input
        try:
            wdl_input_dict = fill_wdl_input(request, j)
        except Exception as ex:
            return HttpResponseBadRequest('Error when instantiating workflow.')


        return render(request, 'analysis/home.html', {'msg': 'post view'})

