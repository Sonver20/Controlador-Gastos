#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py - Gerenciador de configuracoes persistentes do app.
Salva em JSON na mesma pasta do app. Sobrevive reinicializacoes.
"""

import json
import os


class Config:
    """Gerencia configuracoes do app em um arquivo JSON simples."""

    def __init__(self, config_path: str = "app_config.json"):
        self.config_path = os.path.abspath(config_path)
        self._data = self._load()

    def _load(self) -> dict:
        """Carrega o JSON do disco ou retorna dict vazio."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self) -> None:
        """Salva o dict atual no disco."""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default=None):
        """Pega um valor da config."""
        return self._data.get(key, default)

    def set(self, key: str, value) -> dict:
        """Salva um valor e persiste no disco."""
        self._data[key] = value
        self._save()
        return {"success": True, "message": "Configuracao salva."}

    def get_theme(self) -> dict:
        """Retorna o tema salvo ou 'light' como padrao."""
        return {"success": True, "theme": self.get("theme", "light")}

    def set_theme(self, theme: str) -> dict:
        """Salva a preferencia de tema."""
        return self.set("theme", theme)
