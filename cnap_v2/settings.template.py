"""
Django settings for cnap_v2 project.

Generated by 'django-admin startproject' using Django 2.0.6.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.0/ref/settings/
"""

import os
import sys
import datetime

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# add to the python path and import a utility module
sys.path.append(BASE_DIR)
from helpers import utils

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '1+ctigmygs**gkf5b#2g*a3ff)h$8tfkb2%oq&q@d41e&et6=p'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['{{domain}}', ]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'rest_framework',
    'django_filters',
    'transfer_app.apps.TransferAppConfig',
    'custom_auth.apps.CustomAuthConfig',
    'analysis.apps.AnalysisConfig',
    'base.apps.BaseConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cnap_v2.urls'

MAIN_TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [MAIN_TEMPLATE_DIR,],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cnap_v2.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.0/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')


# Settings specific to REST framework:
REST_FRAMEWORK = {

    # At minimum, we don't allow any unauthenticated access.
    # Specific views may have admin- or user-specific privileges
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',)
}


###############################################################################
# Parameters for Celery queueing
###############################################################################
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
###############################################################################
###############################################################################



###############################################################################
# Configuration for Sites framework:
###############################################################################
SITE_ID = 1
###############################################################################
###############################################################################



###############################################################################
# some identifiers for consistent reference:
###############################################################################
GOOGLE = 'google'
AWS = 'aws'
GOOGLE_DRIVE = 'Google Drive'
DROPBOX = 'Dropbox'
WDL = 'wdl'
PY_SUFFIX = '.py'
###############################################################################
###############################################################################



###############################################################################
# Read some config files to set some variables 
###############################################################################

# Read the general configuration file, which will load the settings 
# appropriate for the environment

additional_sections = [GOOGLE_DRIVE, DROPBOX]
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
CONFIG_PARAMS = utils.read_general_config(os.path.join(CONFIG_DIR, 'general.cfg'), additional_sections)
# the jinja templater makes booleans as True, False, which are interpreted as strings
# thus, we need to cast them to booleans here.  Can't use bool(...) method since it evaluates
# non-empty strings to True
for key, val in CONFIG_PARAMS.items():
    if val=='True' or val == 'true':
        CONFIG_PARAMS[key] = True
    elif val=='False' or val == 'false':
        CONFIG_PARAMS[key] = False

# using the value of EXPIRATION_PERIOD_DAYS from the config, set a timedelta:
# This logic could be altered as desired:
EXPIRATION_PERIOD = datetime.timedelta(days=int(CONFIG_PARAMS['expiration_period_days']))

additional_sections = [GOOGLE_DRIVE, DROPBOX, GOOGLE]
LIVE_TEST_CONFIG_PARAMS = utils.load_config(os.path.join(CONFIG_DIR, 'live_tests.cfg'), additional_sections)


# Configuration for upload providers and compute environments:

UPLOADER_CONFIG = {
    'CONFIG_PATH' : os.path.join(CONFIG_DIR, 'uploaders.cfg'),

    # for each item in the following dictionary, there needs to be a section 
    # header in the config file located at UPLOADER_CONFIG.CONFIG_PATH
    'UPLOAD_SOURCES' : [
        DROPBOX,
        GOOGLE_DRIVE
    ]
}

DOWNLOADER_CONFIG = {
    'CONFIG_PATH' : os.path.join(CONFIG_DIR, 'downloaders.cfg'),

    # for each item in the following dictionary, there needs to be a section 
    # header in the config file located at UPLOADER_CONFIG.CONFIG_PATH
    'DOWNLOAD_DESTINATIONS' : [
        DROPBOX,
        GOOGLE_DRIVE
    ]
}
###############################################################################
###############################################################################



###############################################################################
# Auth/user parametersL
###############################################################################
# Register our custom authentication/user:
AUTH_USER_MODEL = 'custom_auth.CustomUser'
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
###############################################################################
###############################################################################



###############################################################################
# Other parameters.  See notes on each.
###############################################################################
# if using gmail, need to have the credentials accessible
# can be blank, if not being used.
EMAIL_CREDENTIALS_FILE = '{{email_credentials_json}}'
EMAIL_ENABLED = {{email_enabled}}
###############################################################################
###############################################################################





###############################################################################
# Constants from the GUI-schema for easy/consistent reference
# These match the various keys in the GUI JSON file.  If it changes there
# it only needs to change in this single location.
###############################################################################

INPUT_ELEMENTS = 'input_elements'
DISPLAY_ELEMENT = 'display_element'
HANDLER = 'handler'
TARGET = 'target'
TARGET_IDS = 'target_ids'
NAME = 'name'
WORKFLOW_ID = 'workflow_id'
VERSION_ID = 'version_id'
###############################################################################
###############################################################################




###############################################################################
# Parameters set during workflow ingestion process
###############################################################################
# The ingestion scripts place files in particular locations, and
# we can parse the config file there to get those parameters

# read the config file and extract the parameters we need:
ingestion_dir = os.path.join(BASE_DIR, 'workflow_ingestion')
ingestion_config_path = os.path.join(ingestion_dir, 'config.cfg')
ingestion_config_dict = utils.load_config(ingestion_config_path)

# the name of the django-ready html template that was auto-created
HTML_TEMPLATE_NAME = ingestion_config_dict['final_html_template_filename']

# the template for the WDL input.  The keys are the inputs in the WDL file and they point
# at WDL "types" (e.g. "String", "Array[File]").  To be used in creating
# final inputs to the workflow runner
WDL_INPUTS_TEMPLATE_NAME = ingestion_config_dict['input_template_json']

# the central location where we store all the WDL workflows and associated files:
WORKFLOWS_DIR = ingestion_config_dict['workflows_dir']

# the name of the file specifying the GUI.  This is the one created by a workflow
# developer.  It is NOT the GUI "reference specification" or schema.  This will
# be found in each workflow directory.  This key just tells us which filename
# to look for
USER_GUI_SPEC_NAME = ingestion_config_dict['gui_spec']

# the name of the javascript file that supports the dynamic content of the UI
FORM_JAVASCRIPT_NAME = ingestion_config_dict['final_javascript_filename']

# the name of the css file that supports dynamic styling of the UI for workflows
FORM_CSS_NAME = ingestion_config_dict['final_css_filename']

# the name of a directory where we work on files before depositing in a final
# location
STAGING_DIR = ingestion_config_dict['staging_dir']

# the name of the main WDL file:
MAIN_WDL = ingestion_config_dict['main_wdl']
###############################################################################
###############################################################################





###############################################################################
# JAR files for workflow runner
###############################################################################

WOMTOOL_JAR = os.path.join(BASE_DIR, 'etc', 'womtool-36.jar') # Broad WOMTool JAR file
CROMWELL_JAR = os.path.join(BASE_DIR, 'etc', 'cromwell-36.jar') # Broad Cromwell JAR
###############################################################################
###############################################################################




###############################################################################
# Parameters for job submission
###############################################################################

# the path of a diretory where temporary job files are stored
JOB_STAGING_DIR = os.path.join(BASE_DIR, 'tmp_staging')

# the location of a cromwell server.  Should be auto-filled during app setup
CROMWELL_SERVER_URL = '{{cromwell_server_url}}'

# If a job fails, do we automatically inform a client?
# If the admins wish to debug a failure (WITHOUT sending auto email to client)
# then this should be set to True (True --> silent --> no email)
SILENT_CLIENTSIDE_FAILURE = True
###############################################################################
###############################################################################

# These are "email addresses" to use in the unit tests.
# Keeping them here allows us to avoid sending emails in those cases
ADMIN_TEST_EMAIL = 'admin@admin.com'
REGULAR_TEST_EMAIL = 'user@foobarbaz.com'
OTHER_TEST_EMAIL = 'other-user@foobarbaz.com'
YET_ANOTHER_TEST_EMAIL = 'yet-another-user@foobarbaz.com'
TEST_EMAIL_ADDRESSES = [ADMIN_TEST_EMAIL, REGULAR_TEST_EMAIL, OTHER_TEST_EMAIL, YET_ANOTHER_TEST_EMAIL]
