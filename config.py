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

    def get_language(self) -> dict:
        """Retorna o idioma salvo ou 'pt' como padrao."""
        return {"success": True, "language": self.get("language", "pt")}

    def set_language(self, language: str) -> dict:
        """Salva a preferencia de idioma ('pt' ou 'en')."""
        return self.set("language", language)

    def get_primary_color(self) -> dict:
        """
        Retorna a cor principal salva ou 'violet' como padrao (cor
        historica do app). O valor pode ser o id de uma paleta pre-definida
        (ex.: 'violet', 'blue', 'emerald', 'red', 'orange') ou uma cor
        customizada em hexadecimal (ex.: '#8b5cf6'), escolhida livremente
        pelo usuario -- quem decide como interpretar isso (aplicar uma
        paleta pronta ou gerar uma escala a partir do hex) e o frontend.
        """
        return {"success": True, "color": self.get("primary_color", "violet")}

    def set_primary_color(self, color: str) -> dict:
        """Salva a preferencia de cor principal (id de paleta ou hex)."""
        return self.set("primary_color", color)
