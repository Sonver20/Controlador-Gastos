#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
version.py - Versao do Controlador de Gastos.

Segue Semantic Versioning (https://semver.org/lang/pt-BR/): MAJOR.MINOR.PATCH

- MAJOR: mudanca incompativel (ex.: quebra o formato do banco de dados,
  remove uma funcionalidade, muda o comportamento de algo existente)
- MINOR: nova funcionalidade adicionada de forma compativel com o que ja
  existia (nada quebra para quem ja usava o app)
- PATCH: correcao de bug, sem adicionar funcionalidade nova

Ao lancar uma nova versao, atualize APP_VERSION aqui e registre o que
mudou em CHANGELOG.md. Esta e a UNICA fonte de verdade da versao: o
rodape do app (index.html/script.js) busca esse valor via
Api.get_app_version(), entao nao precisa (e nao deve) ser editado em
mais nenhum outro lugar.
"""

APP_VERSION = "2.1.0"
