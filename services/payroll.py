#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
services/payroll.py - Servico de Folha de Pagamento e Tributos.

Contem o calculo de ferias (calcular_ferias) e as tabelas de aliquotas de
INSS/IRRF usadas nele. É um módulo de funções puras: não acessa o banco
de dados, nem qualquer estado externo -- só recebe um salário bruto e
devolve os valores calculados.
"""

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict

from .decimal_utils import to_decimal, TWO_PLACES


def calcular_ferias(salario_bruto: Any) -> Dict[str, Any]:
    """
    Calcula o valor liquido de ferias a partir do salario bruto:
    1/3 constitucional, desconto de INSS (progressivo por faixa) e de
    IRRF (com o desconto simplificado), resultando no salario liquido.
    """
    try:
        # Valores de entrada/saida em centavos exatos; os calculos
        # intermediários (bases, faixas) mantém precisão total e só
        # são arredondados para 2 casas na hora de montar o retorno.
        sb = to_decimal(salario_bruto)
        constitucional = sb / Decimal("3")
        total_bruto = sb + constitucional

        # INSS progressivo
        faixas_inss = [
            (Decimal("1621.00"), Decimal("0.075")),
            (Decimal("2902.84"), Decimal("0.09")),
            (Decimal("4354.27"), Decimal("0.12")),
            (Decimal("8475.55"), Decimal("0.14")),
        ]
        anterior = Decimal("0")
        inss_val = Decimal("0")
        for limite, aliquota in faixas_inss:
            if total_bruto >= limite:
                inss_val += (limite - anterior) * aliquota
                anterior = limite
            else:
                inss_val += (total_bruto - anterior) * aliquota
                break

        base_irrf = total_bruto - inss_val

        # IRRF
        faixas_irrf = [
            (Decimal("2428.80"), Decimal("0"), Decimal("0.00")),
            (Decimal("2826.65"), Decimal("0.075"), Decimal("182.16")),
            (Decimal("3751.05"), Decimal("0.15"), Decimal("394.16")),
            (Decimal("4664.68"), Decimal("0.225"), Decimal("675.49")),
        ]
        irrf_val = Decimal("0")
        for limite, aliquota, parcela in faixas_irrf:
            if base_irrf <= limite:
                irrf_val = (base_irrf * aliquota) - parcela
                break
        else:
            irrf_val = (base_irrf * Decimal("0.275")) - Decimal("908.73")

        # Desconto adicional (nova regra)
        if base_irrf <= Decimal("5000.00"):
            desconto_adicional = base_irrf
        elif base_irrf <= Decimal("7350.00"):
            desconto_adicional = Decimal("978.62") - (Decimal("0.133145") * base_irrf)
        else:
            desconto_adicional = Decimal("0")

        irrf_final = max(Decimal("0"), irrf_val - desconto_adicional)
        salario_liquido = base_irrf - irrf_final

        def q(d: Decimal) -> Decimal:
            return d.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        return {
            "success": True,
            "salario_bruto": q(sb),
            "terco_constitucional": q(constitucional),
            "total_bruto": q(total_bruto),
            "inss": q(inss_val),
            "base_irrf": q(base_irrf),
            "irrf_calculado": q(irrf_val),
            "desconto_adicional": q(desconto_adicional),
            "irrf_final": q(irrf_final),
            "salario_liquido": q(salario_liquido),
        }
    except (InvalidOperation, ValueError, TypeError) as e:
        return {"success": False, "message": str(e)}
