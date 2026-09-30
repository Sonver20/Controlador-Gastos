#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/main.py - Executa TODOS os testes do Controlador de Gastos.

    python3 tests/main.py             # todos os testes, saída detalhada
    python3 tests/main.py -q          # silencioso: só falhas e o resumo
    python3 tests/main.py config api  # só os módulos cujo nome contém "config" ou "api"
    python3 -m tests.main             # equivalente, a partir da raiz do projeto

Os arquivos `tests/test_*.py` são descobertos automaticamente. O código de
saída é 0 se tudo passou e 1 se houve falha (útil em scripts e no git hook).
"""

import argparse
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

TESTS_DIR = os.path.join(ROOT, "tests")


def _flatten(suite):
    """Percorre uma suíte (que pode conter outras suítes) e devolve cada teste."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _flatten(item)
        else:
            yield item


def build_suite(filters=None):
    """Descobre os testes; se `filters` vier preenchido, mantém só os módulos que os contêm no nome."""
    loader = unittest.TestLoader()
    discovered = loader.discover(start_dir=TESTS_DIR, pattern="test_*.py", top_level_dir=ROOT)
    suite = unittest.TestSuite()
    for test in _flatten(discovered):
        module = type(test).__module__  # ex.: "tests.test_config"
        if not filters or any(f.lower() in module.lower() for f in filters):
            suite.addTest(test)
    return suite


def main(argv=None):
    parser = argparse.ArgumentParser(description="Executa os testes do Controlador de Gastos.")
    parser.add_argument("modulos", nargs="*", help="filtra por parte do nome do módulo (ex.: config, api, migrations)")
    parser.add_argument("-q", "--quiet", action="store_true", help="saída silenciosa (só falhas e o resumo)")
    args = parser.parse_args(argv)

    suite = build_suite(args.modulos)
    if suite.countTestCases() == 0:
        print(f"Nenhum teste encontrado para: {' '.join(args.modulos)}")
        return 2

    runner = unittest.TextTestRunner(verbosity=1 if args.quiet else 2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
