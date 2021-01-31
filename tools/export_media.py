#!/usr/bin/python
from nmj.scanners.local import DirectoryScanner
import sys

base_directory = sys.argv[1]
destination = "test"
if len(sys.argv) == 3:
	destination = sys.argv[2]
scanner = DirectoryScanner(base_directory)
print("FOund %s media files in %s" % (len(scanner.movie_files), base_directory))
for movie in scanner.movie_files:
	movie.create_dummy_for_test(base_directory, destination)

