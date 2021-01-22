# -*- coding: utf-8 -*-
import locale
import os
import requests
import shutil

def to_unicode(text):
	if isinstance(text, str):
		return text

	if hasattr(text, '__unicode__'):
		return text.__unicode__()

	text = str(text)

	try:
		return str(text, 'utf-8')
	except UnicodeError:
		pass

	try:
		return str(text, locale.getpreferredencoding())
	except UnicodeError:
		pass

	return str(text, 'latin1')


def download_image(url, filepath):
	if not os.path.isdir(os.path.dirname(filepath)):
		os.makedirs(os.path.dirname(filepath))
	# r = requests.get(url, stream=True)
	# if r.status_code == 200:
	# 	with open(filepath, 'wb') as f:
	# 		for chunk in r.iter_content(1024):
	# 			f.write(chunk)
	r = requests.get(url, stream=True)
	if r.status_code == 200:
		with open(filepath, 'wb') as f:
			r.raw.decode_content = True
			shutil.copyfileobj(r.raw, f) 