import pandas as pd
import streamlit as st
from services.query_service import run_query

SQL_ESTOQUE = """
SELECT
    COALESCE(SUM(quantidade * custo_unitario), 0) AS valor_estoque
FROM POSICAO_ESTOQUE_ATUAL
WHERE deposito NOT IN ('N CONF', 'AVARIA', 'VENC')
"""

SQL_ESTOQUE_TIPO_MATERIAL = """
SELECT
    tipo_material,
    COUNT(DISTINCT produto) AS qtd_produtos,
    COALESCE(SUM(quantidade * custo_unitario), 0) AS valor_tipo
FROM POSICAO_ESTOQUE_ATUAL
WHERE deposito NOT IN ('N CONF', 'AVARIA', 'VENC')
  AND tipo_material IN ('PA', 'FO', 'MP', 'ME')
GROUP BY tipo_material
ORDER BY tipo_material
"""

SQL_ESTOQUE_PROBLEMA_TOTAL = """
SELECT
    COALESCE(SUM(quantidade * custo_unitario), 0) AS valor_total
FROM POSICAO_ESTOQUE_ATUAL
WHERE deposito IN ('N CONF', 'AVARIA', 'VENC')
"""

SQL_ESTOQUE_PROBLEMA_DETALHE = """
SELECT
    deposito,
    COUNT(DISTINCT produto) AS qtd_produtos,
    COALESCE(SUM(quantidade * custo_unitario), 0) AS valor_deposito
FROM POSICAO_ESTOQUE_ATUAL
WHERE deposito IN ('N CONF', 'AVARIA', 'VENC')
GROUP BY deposito
ORDER BY deposito
"""

def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_kpi():
    try:
        df_total = run_query(SQL_ESTOQUE)
        df_tipo = run_query(SQL_ESTOQUE_TIPO_MATERIAL)

        valor_total = float(df_total.iloc[0]["valor_estoque"] or 0)

        detalhes = []
        tipos_esperados = ["PA", "FO", "MP", "ME"]

        for tipo in tipos_esperados:
            linha = df_tipo[df_tipo["tipo_material"] == tipo]

            if not linha.empty:
                qtd_produtos = int(linha.iloc[0]["qtd_produtos"] or 0)
                valor_tipo = float(linha.iloc[0]["valor_tipo"] or 0)
            else:
                qtd_produtos = 0
                valor_tipo = 0

            detalhes.append(
                f"{tipo}: {qtd_produtos} produtos | {formatar_moeda_br(valor_tipo)}"
            )

        return {
            "nome": "Total de Estoque Mês",
            "valor": valor_total,
            "valor_anterior": valor_total,
            "unidade": "R$",
            "cor": "card-pink",
            "extra": "<br>".join(detalhes),
        }

    except Exception as e:
        st.error(f"Erro no módulo Estoque: {e}")
        return {
            "nome": "Total de Estoque Mês",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-pink",
            "extra": "PA: 0 produtos | R$ 0,00<br>FO: 0 produtos | R$ 0,00<br>MP: 0 produtos | R$ 0,00<br>EM: 0 produtos | R$ 0,00",
        }

def get_kpi_avarias():
    try:
        df_total = run_query(SQL_ESTOQUE_PROBLEMA_TOTAL)
        df_detalhe = run_query(SQL_ESTOQUE_PROBLEMA_DETALHE)

        valor_total = float(df_total.iloc[0]["valor_total"] or 0)

        detalhes = []
        depositos_esperados = ["AVARIA", "VENC", "N CONF"]

        for deposito in depositos_esperados:
            linha = df_detalhe[df_detalhe["deposito"] == deposito]

            if not linha.empty:
                qtd_produtos = int(linha.iloc[0]["qtd_produtos"] or 0)
                valor_deposito = float(linha.iloc[0]["valor_deposito"] or 0)
            else:
                qtd_produtos = 0
                valor_deposito = 0

            detalhes.append(
                f"{deposito}: {qtd_produtos} produtos | {formatar_moeda_br(valor_deposito)}"
            )

        return {
            "nome": "Estoque Avaria / Venc / N Conf",
            "valor": valor_total,
            "valor_anterior": valor_total,
            "unidade": "R$",
            "cor": "card-red",
            "extra": "<br>".join(detalhes)
        }

    except Exception as e:
        st.error(f"Erro no módulo Estoque (Avarias): {e}")
        return {
            "nome": "Estoque Avaria / Venc / N Conf",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-red",
            "extra": "AVARIA: 0 produtos | R$ 0,00<br>VENC: 0 produtos | R$ 0,00<br>N CONF: 0 produtos | R$ 0,00"
        }

def get_serie_mensal():
    return pd.DataFrame({
        "Mês": ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
        "Valor": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    })