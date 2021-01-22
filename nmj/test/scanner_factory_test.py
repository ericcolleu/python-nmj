# -*- coding: utf-8 -*-
from nmj.scanner_factory import ScannerFactory, ScannerNotFound
import unittest
from unittest import mock

class ScannerFactoryTestCase(unittest.TestCase):
	def test_01a(self):
		"""ScanFactory: register scanner"""
		scanner = "dummy scanner"
		factory = ScannerFactory()
		factory.register_scanner(scanner)
		self.assertEqual(factory.scanners, [scanner, ])

	def test_02a(self):
		"""ScanFactory: get_scanner, scanner found"""
		scanner1 = mock.MagicMock()
		scanner1.accept = mock.MagicMock(return_value=False)
		scanner2 = mock.MagicMock()
		scanner2.accept = mock.MagicMock(return_value=True)
		filepath = "/path/to/the/file"
		# scanner1.accept(filepath)
		# scanner2.accept(filepath)
		factory = ScannerFactory()
		factory.register_scanner(scanner1, scanner2)
		self.assertEqual(scanner2, factory.get_scanner(filepath))
		scanner1.accept.assert_called_once()
		scanner2.accept.assert_called_once()

	def test_03a(self):
		"ScannerFactory: get scanner, scanner not found"
		scanner1 = mock.MagicMock()
		scanner1.accept = mock.MagicMock(return_value=False)
		scanner2 = mock.MagicMock()
		scanner2.accept = mock.MagicMock(return_value=False)
		filepath = "/path/to/the/file"
		factory = ScannerFactory()
		factory.register_scanner(scanner1, scanner2)
		self.assertRaises(ScannerNotFound, factory.get_scanner, filepath)
		scanner1.accept.assert_called_once()
		scanner2.accept.assert_called_once()

if __name__ == "__main__":
	unittest.main()


