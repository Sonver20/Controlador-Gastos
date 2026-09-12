#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
decimal_utils.py - Utilitarios de conversao para decimal.Decimal.

Módulo compartilhado por todas as camadas (database.py e services/*.py),
sem depender de SQLite nem de nenhuma regra de negocio. Existe para que
database.py e os services não precisem duplicar a lógica de "como
transformar uma entrada crua (string, float, int) em um Decimal exato".
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

TWO_PLACES = Decimal("0.01")
THREE_PLACES = Decimal("0.001")


def _parse_decimal(value: Any, places: Decimal, normalize_comma: bool) -> Decimal:
    """
    Nucleo compartilhado de to_decimal/to_quantity: converte str/int/float/
    Decimal em Decimal, arredondado para `places` casas decimais.

    Floats são convertidos via `str(value)` antes de virar Decimal, para
    evitar herdar o "ruido" binario do float (ex.: Decimal(19.99) viraria
    19.988999999999999769..., enquanto Decimal(str(19.99)) vira exatamente
    "19.99"). `normalize_comma` decide se uma string tipo "5,50" deve virar
    "5.50" antes do parse -- usado por to_quantity, mas NAO por to_decimal
    (que espera "." como separador; chamadores que recebem virgula do
    usuario, como o servico financeiro no cadastro em massa, normalizam
    isso antes de chamar to_decimal). Levanta InvalidOperation/ValueError/
    TypeError para entradas invalidas, para que os chamadores possam
    tratar o erro.
    """
    if isinstance(value, Decimal):
        d = value
    elif isinstance(value, float):
        d = Decimal(str(value))
    elif isinstance(value, str):
        cleaned = value.strip()
        if normalize_comma:
            cleaned = cleaned.replace(",", ".")
        if cleaned == "":
            raise InvalidOperation("valor vazio")
        d = Decimal(cleaned)
    else:
        d = Decimal(value)
    return d.quantize(places, rounding=ROUND_HALF_UP)


def to_decimal(value: Any) -> Decimal:
    """Converte qualquer valor recebido (str, int, float, Decimal) em um
    Decimal arredondado para 2 casas decimais (centavos)."""
    return _parse_decimal(value, TWO_PLACES, normalize_comma=False)


def to_quantity(value: Any) -> Decimal:
    """Converte um valor de quantidade (pode ser fracionaria, ex.: peso em
    kg como '0.750') em Decimal com ate 3 casas decimais."""
    return _parse_decimal(value, THREE_PLACES, normalize_comma=True)
