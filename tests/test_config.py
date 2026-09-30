"""
tests/test_config.py - Configurações persistentes (tema, idioma, cor, moeda, mês de férias).
"""

import unittest
import os
import tempfile
from config import Config


class TestConfig(unittest.TestCase):
    """Testa persistencia de configuracoes."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, "test_config.json")
        self.cfg = Config(config_path=self.config_path)

    def tearDown(self):
        if os.path.exists(self.config_path):
            os.unlink(self.config_path)
        os.rmdir(self.tmpdir)

    def test_theme_default(self):
        self.assertEqual(self.cfg.theme, "light")

    def test_set_theme(self):
        self.cfg.theme = "dark"
        # Recarrega do disco
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.theme, "dark")

    def test_language_default(self):
        self.assertEqual(self.cfg.language, "pt")

    def test_set_language(self):
        self.cfg.language = "en"
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.language, "en")

    def test_primary_color_default(self):
        self.assertEqual(self.cfg.primary_color, "violet")

    def test_set_primary_color_preset(self):
        self.cfg.primary_color = "blue"
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.primary_color, "blue")

    def test_set_primary_color_custom_hex(self):
        self.cfg.primary_color = "#ff8800"
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.primary_color, "#ff8800")

    def test_currency_default(self):
        self.assertEqual(self.cfg.currency, "BRL")

    def test_set_currency(self):
        self.cfg.currency = "USD"
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.currency, "USD")

    def test_vacation_month_default(self):
        self.assertEqual(self.cfg.vacation_month, 7)

    def test_set_vacation_month(self):
        self.cfg.vacation_month = 12
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.vacation_month, 12)

    def test_get_set_custom_key(self):
        self.cfg.set("custom_key", "custom_value")
        self.assertEqual(self.cfg.get("custom_key"), "custom_value")
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.get("custom_key"), "custom_value")

    def test_get_missing_key_returns_default(self):
        self.assertIsNone(self.cfg.get("missing"))
        self.assertEqual(self.cfg.get("missing", "default"), "default")

    def test_persistence_survives_reinit(self):
        self.cfg.theme = "dark"
        self.cfg.set("language", "pt-BR")
        cfg2 = Config(config_path=self.config_path)
        self.assertEqual(cfg2.theme, "dark")
        self.assertEqual(cfg2.get("language"), "pt-BR")
