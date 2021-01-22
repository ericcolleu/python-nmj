# -*- coding: utf-8 -*-

class ScannerNotFound(Exception): pass
class UnknownMediaType(Exception): pass

class ScannerFactory(object):
	def __init__(self):
		self.scanners = []

	def register_scanner(self, *scanner):
		self.scanners.extend(scanner)

	def get_scanner(self, media):
		for scanner in self.scanners:
			if scanner.accept(media):
				return scanner
		raise ScannerNotFound("No scanner found for %s" % media)

	def update_media_type(self, media):
		for scanner in self.scanners:
			if scanner.accept(media):
				return
		raise UnknownMediaType("Don't found media type %s" % media)

