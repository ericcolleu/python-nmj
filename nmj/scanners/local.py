import os
import logging

_LOGGER = logging.getLogger(__name__)

class MovieFile(object):
	def __init__(self, path):
		self.filename = os.path.basename(path)
		self.title, self.extension = os.path.splitext(self.filename)
		self.path = path
		self.location = os.path.dirname(path)

	def create_dummy_for_test(self, src_base_dir, dst_base_dir):
		dummy = self.path.replace(src_base_dir, dst_base_dir)
		filedir = os.path.dirname(dummy)
		if not os.path.isdir(filedir):
			os.makedirs(filedir)
		open("%s" % dummy, "w+").close()

	def __str__(self):
		return self.title

class DirectoryScanner(object):
	def __init__(self, *base_directories):
		self._basedirs = base_directories
		self.movie_files = self._scan_dir(".avi", ".mkv", ".vob", ".iso", ".mp4", ".ogm")

	def _scan_dir(self, *extensions):
		result = []
		for base_dir in self._basedirs:
			for root, dirs, files in os.walk(base_dir, followlinks=True):
				if self._ignore_dir(files):
					_LOGGER.debug("Ignoring directory %s", root)
					del files[:]
					del dirs[:]
					continue
				for filedir in dirs[:]:
					if filedir.startswith("."):
						dirs.remove(filedir)
				for video in files:
					_, ext = os.path.splitext(video)
					if ext in extensions:
						result.append(MovieFile(os.path.join(root, video)))
				if "BDMV" in dirs:
					result.append(MovieFile(root))
		return result

	def _ignore_dir(self, files):
		return ".no_all.nmj" in files or ".no_video.nmj" in files
