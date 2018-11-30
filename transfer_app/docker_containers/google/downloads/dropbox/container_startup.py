#! /usr/bin/python3

import os
import sys
import io
import subprocess
import argparse
import dropbox
import datetime
from Crypto.Cipher import DES
import base64
import requests
from google.cloud import storage, logging
from apiclient.discovery import build

WORKING_DIR = '/workspace'
DEFAULT_TIMEOUT = 60
DEFAULT_CHUNK_SIZE = 100*1024*1024 # dropbox says <150MB per chunk
HOSTNAME_REQUEST_URL = 'http://metadata/computeMetadata/v1/instance/hostname'
GOOGLE_BUCKET_PREFIX = 'gs://'

def create_logger():
	"""
	Creates a log in Stackdriver
	"""
	instance_name = get_hostname()
	logname = '%s.log' % instance_name
	logging_client = logging.Client()
	logger = logging_client.logger(logname)
	return logger

def notify_master(params, logger, error=False):
	'''
	This calls back to the head machine to let it know the work is finished.
	'''
	logger.log_text('Notifying the master that this job has completed')

	# the payload dictinary:
	d = {}

	# prepare the token which identifies the VM as a 'known' sender
	token = params['token']
	obj=DES.new(params['enc_key'], DES.MODE_ECB)
	enc_token = obj.encrypt(token)
	b64_str = base64.encodestring(enc_token)
	d['token'] = b64_str

	# Other required params to return:
	d['transfer_pk'] = params['transfer_pk']
	d['success'] = 0 if error else 1
	base_url = params['callback_url']
	response = requests.post(base_url, data=d)
	logger.log_text('Status code: %s' % response.status_code)
	logger.log_text('Response text: %s' % response.text)


def download_to_disk(params, logger):
	'''
	Downloads the file from the bucket to the local disk.
	'''
	src = params['resource_path']
	src_without_prefix = src[len(GOOGLE_BUCKET_PREFIX):] # remove the prefix
	contents = src_without_prefix.split('/')
	bucket_name = contents[0]
	object_name = '/'.join(contents[1:])
	basename = os.path.basename(object_name)
	local_path = os.path.join(WORKING_DIR, basename)

	storage_client = storage.Client()
	source_bucket = storage_client.get_bucket(bucket_name)
	source_blob = source_bucket.blob(object_name)
	logger.log_text('Download file from %s to %s' % (src, local_path))
	source_blob.download_to_filename(local_path)
	logger.log_text('Completed download to disk')
	return local_path


def send_to_dropbox(local_filepath, params, logger):
	'''
	local_filepath is the path on the VM/container of the file that
	was already downloaded.
	'''
	token = params['access_token']
	client = dropbox.dropbox.Dropbox(token, timeout=DEFAULT_TIMEOUT)
	file_size = os.path.getsize(local_filepath)

	stream = open(local_filepath, 'rb')
	path_in_dropbox = '%s/%s' % (params['dropbox_destination_folderpath'], os.path.basename(local_filepath))
	if file_size <= DEFAULT_CHUNK_SIZE:
		client.files_upload(stream.read(), path_in_dropbox)
	else:
		i = 1
		session_start_result = client.files_upload_session_start(stream.read(DEFAULT_CHUNK_SIZE))
		cursor=dropbox.files.UploadSessionCursor(session_start_result.session_id, offset=stream.tell())
		commit=dropbox.files.CommitInfo(path=path_in_dropbox)
		while stream.tell() < file_size:
			logger.log_text('Sending chunk %s' % i)
			try:
				if (file_size-stream.tell()) <= DEFAULT_CHUNK_SIZE:
					logger.log_text('Finishing transfer and committing')
					client.files_upload_session_finish(stream.read(DEFAULT_CHUNK_SIZE), cursor, commit)
				else:
					logger.log_text('About to send chunk')
					logger.log_text('Prior to chunk transfer, cursor=%d, stream=%d' % (cursor.offset, stream.tell()))
					client.files_upload_session_append_v2(stream.read(DEFAULT_CHUNK_SIZE), cursor)
					cursor.offset = stream.tell()
					logger.log_text('Done with sending chunk %s' % i)
			except dropbox.exceptions.ApiError as ex:
				logger.log_text('ERROR: Raised ApiError!')
				if ex.error.is_incorrect_offset():
					logger.log_text('ERROR: The error raised was an offset error.  Correcting the cursor and stream offset')
					correct_offset = ex.error.get_incorrect_offset().correct_offset
					cursor.offset = correct_offset
					stream.seek(correct_offset)
				else:
					logger.log_text('ERROR: API error was raised, but was not offset error')
					raise ex
			except requests.exceptions.ConnectionError as ex:
				logger.log_text('ERROR: Caught a ConnectionError exception')
				# need to rewind the stream
				logger.log_text('At this point, cursor=%d, stream=%d' % (cursor.offset, stream.tell()))
				cursor_offset = cursor.offset
				stream.seek(cursor_offset)
				logger.log_text('After rewind, cursor=%d, stream=%d' % (cursor.offset, stream.tell()))
				logger.log_text('Go try that chunk again')
			except requests.exceptions.RequestException as ex:
				logger.log_text('ERROR: Caught an exception during chunk transfer')
				logger.log_text('ERROR: Following FAILED chunk transfer, cursor=%d, stream=%d' % (cursor.offset, stream.tell()))
				raise ex
			i += 1
	stream.close()


def get_hostname():
	headers = {'Metadata-Flavor':'Google'}
	response = requests.get(HOSTNAME_REQUEST_URL, headers=headers)
	content = response.content.decode('utf-8')
	instance_name = content.split('.')[0]
	return instance_name


def kill_instance(params):
	'''
	Removes the virtual machine
	'''
	instance_name = get_hostname()
	compute = build('compute', 'v1')
	compute.instances().delete(project=params['google_project_id'],
		zone=params['google_zone'], 
	instance=instance_name).execute()


def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument("-token", help="A token for identifying the container with the main application", dest='token', required=True)
	parser.add_argument("-key", help="An encryption key for identifying the container with the main application", dest='enc_key', required=True)
	parser.add_argument("-pk", help="The primary key of the transfer", dest='transfer_pk', required=True)
	parser.add_argument("-url", help="The callback URL for communicating with the main application", dest='callback_url', required=True)
	parser.add_argument("-path", help="The source of the file that is being downloaded", dest='resource_path', required=True)
	parser.add_argument("-dropbox", help="The access token for Dropbox", dest='access_token', required=True)
	parser.add_argument("-d", help="The folder in Dropbox where the file will go", dest='dropbox_destination_folderpath', required=True)
	parser.add_argument("-proj", help="Google project ID", dest='google_project_id', required=True)
	parser.add_argument("-zone", help="Google project zone", dest='google_zone', required=True)
	args = parser.parse_args()
	params = {}
	params['token'] = args.token
	params['enc_key'] =  args.enc_key
	params['transfer_pk'] = args.transfer_pk
	params['callback_url'] = args.callback_url
	params['resource_path'] = args.resource_path
	params['access_token'] = args.access_token
	params['dropbox_destination_folderpath'] = args.dropbox_destination_folderpath
	params['google_project_id'] = args.google_project_id
	params['google_zone'] = args.google_zone
	return params


if __name__ == '__main__':
	try:
		params = parse_args()
		os.mkdir(WORKING_DIR)
		logger = create_logger()
		local_filepath = download_to_disk(params, logger)
		send_to_dropbox(local_filepath, params, logger)
		notify_master(params, logger)
		kill_instance(params)
	except Exception as ex:
		logger.log_text('ERROR: Caught some unexpected exception.')
		logger.log_text(str(type(ex)))
		logger.log_text(ex)
		notify_master(params, logger, error=True)
