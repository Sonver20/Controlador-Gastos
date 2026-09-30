"""
tests/test_version.py - Formato da versão (SemVer).
"""

import unittest


class TestVersion(unittest.TestCase):
    """Garante que a versao segue o formato MAJOR.MINOR.PATCH do SemVer."""

    def test_version_format(self):
        from version import APP_VERSION
        parts = APP_VERSION.split(".")
        self.assertEqual(len(parts), 3, "versao deve seguir o formato MAJOR.MINOR.PATCH")
        for p in parts:
            self.assertTrue(p.isdigit(), f"'{p}' deveria ser numerico")
