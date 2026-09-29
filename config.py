#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py - Gerenciador de configuracoes persistentes do app.
Salva em JSON na mesma pasta do app. Sobrevive reinicializacoes.

Cada preferencia simples (tema, idioma, cor, moeda, mes de ferias) e
declarada como um `ConfigProperty`: um descriptor generico que sabe ler
e escrever sua propria chave em `Config._data` e persistir no disco.
Antes, cada preferencia tinha seu proprio par get_x()/set_x() -- metodos
identicos entre si, mudando so o nome da chave e o valor padrao. Com o
descriptor, adicionar uma preferencia nova (como `currency` abaixo) e
so mais uma linha; nao e preciso escrever get/set novos.

O "success"/mensagem que o frontend recebe NAO mora aqui: isso e uma
preocupacao da ponte com o JS (app.py/Api), nao de armazenamento. Config
e so o armazenamento -- le/escreve valores crus, sem embrulhar resposta.
"""

import json
import os


class ConfigProperty:
    """
    Descriptor generico para uma preferencia simples persistida no JSON
    do app. `cfg.theme` le `obj.get("theme", default)`; `cfg.theme = x`
    grava e persiste via `obj.set("theme", x)`.
    """

    def __init__(self, key: str, default):
        self.key = key
        self.default = default

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.get(self.key, self.default)

    def __set__(self, obj, value) -> None:
        obj.set(self.key, value)


class Config:
    """Gerencia configuracoes do app em um arquivo JSON simples."""

    # Tema ("light"/"dark"), idioma ("pt"/"en") e cor principal (id de
    # paleta ou hex) -- ver scripts/core/theme.js, i18n.js e color.js.
    theme = ConfigProperty("theme", "light")
    language = ConfigProperty("language", "pt")
    primary_color = ConfigProperty("primary_color", "violet")
    # Codigo ISO 4217 da moeda de EXIBICAO (ex.: "BRL", "USD", "EUR",
    # "GBP") -- ver CURRENCIES em app.py para a lista suportada nesta
    # primeira versao (moedas comuns de 2 casas decimais; moedas que
    # funcionam diferente, como Iene, ficam de fora por enquanto). E so
    # formatacao: o numero digitado pelo usuario nao muda, so o simbolo
    # exibido (Intl.NumberFormat, no frontend, ja sabe renderizar o
    # simbolo certo por locale a partir do codigo).
    currency = ConfigProperty("currency", "BRL")
    # Mes (1-12) usado pelo calendario de salarios para destacar o
    # recebimento de ferias -- ver services/scheduler.py.
    vacation_month = ConfigProperty("vacation_month", 7)

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
        """Pega um valor cru da config (chave livre, fora das properties acima)."""
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        """Salva um valor cru e persiste no disco."""
        self._data[key] = value
        self._save()
