#!/usr/bin/python
import logging
import optparse
import os
import time

from nmj.updater import NMJUpdater


_LOGGER = logging.getLogger("nmj")
def get_lock(root_dir):
	while os.path.isfile(os.path.join(root_dir, "pynmj.lock")):
		time.sleep(0.5)
	fd = open(os.path.join(root_dir, "pynmj.lock"), "w+")
	fd.write("lock\n")
	fd.close()

def release_lock(root_dir):
	try:
		os.remove(os.path.join(root_dir, "pynmj.lock"))
	except:
		pass

def parse_options():
	parser = optparse.OptionParser()

	parser.add_option(
		"-n", "--clean-name",
		dest="clean_name", action="store_true", default=False,
		help="Clean videos file names",
	)
	return parser.parse_args()

def main():
	logging.basicConfig(level=logging.DEBUG)
	_LOGGER.setLevel(logging.INFO)
	options, arguments = parse_options()
	try:
		try:
			get_lock(arguments[0])
			updater = NMJUpdater(arguments[0], "local_directory")
			if options.clean_name:
				updater.clean_names()
			medias = updater.scan_dir()
			_LOGGER.info("Found %s medias", len(medias))
			for rank, media in enumerate(medias):
				_LOGGER.info("Media %s/%s", rank+1, len(medias))
				updater.search_media_and_add(media)
			_LOGGER.info("Cleaning DB...")
			updater.clean()
			_LOGGER.info("Done")
		except:
			import traceback;traceback.print_exc()
	finally:
		release_lock(arguments[0])

if __name__ == "__main__":
	main()

