# -*- coding: utf-8 -*-
import locale
import os
import requests
import shutil
import logging
import tempfile
import PIL
from PIL import Image


_LOGGER = logging.getLogger(__name__)
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

def resize_image(orig, dest, width):
	img = Image.open(orig)
	wpercent = (width/float(img.size[0]))
	hsize = int((float(img.size[1])*float(wpercent)))
	img = img.resize((width,hsize), PIL.Image.ANTIALIAS)
	img.save(dest)

def download_image(url, filepath, width=None):
	if os.path.isfile(filepath):
		return
	if not os.path.isdir(os.path.dirname(filepath)):
		os.makedirs(os.path.dirname(filepath))
	r = requests.get(url, stream=True)
	if r.status_code == 200:
		with tempfile.NamedTemporaryFile() as f:
			r.raw.decode_content = True
			shutil.copyfileobj(r.raw, f)
			if width:
				resize_image(f.name, filepath, width)
			else:
				shutil.copyfile(f.name, filepath)

def print_details(object_, prefix="", logger=None):
	logger = logger or _LOGGER
	logger.debug("%s %s details (%s):", prefix, object, type(object_))
	logger.debug("%s %s:", prefix, dir(object_))
	for attr in dir(object_):
		if not attr.startswith("__"):
			try:
				logger.debug("%s %s = %s", prefix, attr, getattr(object_, attr))
			except:
				logger.debug("%s %s = Unknown value", prefix, attr)
			
