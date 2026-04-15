import pandas as pd
import streamlit as st
from services.query_service import run_query

SQL_OF_DISPERSAO_ATUAL = """
SELECT
    COUNT(*) AS qtd_ofs,
    COALESCE(SUM(qtde_of), 0) AS qtde_produzida_total
FROM (
    SELECT
        numero_of,
        MAX(qtde_produzida) AS qtde_of
    FROM APONTAMENTO
    WHERE DATE(data_inicial) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
      AND DATE(data_inicial) <= CURDATE()
      AND UPPER(TRIM(desc_operacao)) = 'DISPERSAO'
    GROUP BY numero_of
) base
"""

SQL_OF_DISPERSAO_ANTERIOR = """
SELECT
    COUNT(*) AS qtd_ofs,
    COALESCE(SUM(qtde_of), 0) AS qtde_produzida_total
FROM (
    SELECT
        numero_of,
        MAX(qtde_produzida) AS qtde_of
    FROM APONTAMENTO
    WHERE DATE(data_inicial) >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
      AND DATE(data_inicial) < DATE_FORMAT(CURDATE(), '%Y-%m-01')
      AND UPPER(TRIM(desc_operacao)) = 'DISPERSAO'
    GROUP BY numero_of
) base
"""

SQL_OF_DISPERSAO_APONTAMENTOS_ATUAL = """
SELECT
    COUNT(*) AS qtd_apontamentos,
    COUNT(DISTINCT CONCAT(numero_of, '-', produto)) AS qtd_of_produto
FROM APONTAMENTO
WHERE DATE(data_inicial) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND DATE(data_inicial) <= CURDATE()
  AND UPPER(TRIM(desc_operacao)) = 'DISPERSAO'
"""

def get_kpi():
    try:
        atual = run_query(SQL_OF_DISPERSAO_ATUAL)
        anterior = run_query(SQL_OF_DISPERSAO_ANTERIOR)
        apont = run_query(SQL_OF_DISPERSAO_APONTAMENTOS_ATUAL)

        return {
            "nome": "OF Dispersão Mês",
            "valor": float(atual.iloc[0]["qtd_ofs"] or 0),
            "valor_anterior": float(anterior.iloc[0]["qtd_ofs"] or 0),
            "unidade": "num",
            "cor": "card-pink",
            "qtd_ofs": int(atual.iloc[0]["qtd_ofs"] or 0),
            "qtd_apontamentos": int(apont.iloc[0]["qtd_apontamentos"] or 0),
            "qtd_of_produto": int(apont.iloc[0]["qtd_of_produto"] or 0),
            "qtde_produzida_total": float(atual.iloc[0]["qtde_produzida_total"] or 0),
            "extra_obs": "Estou considarando todos as OF que passam pela Dispersão"
        }
    except Exception as e:
        st.error(f"Erro no módulo OF Dispersão: {e}")
        return {
            "nome": "OF Dispersão Mês",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "num",
            "cor": "card-pink",
            "qtd_ofs": 0,
            "qtd_apontamentos": 0,
            "qtd_of_produto": 0,
            "qtde_produzida_total": 0,
        }

def get_detalhe():
    try:
        atual = run_query(SQL_OF_DISPERSAO_ATUAL)
        apont = run_query(SQL_OF_DISPERSAO_APONTAMENTOS_ATUAL)

        if atual.empty or apont.empty:
            return {
                "qtd_ofs": 0,
                "qtd_apontamentos": 0,
                "qtd_of_produto": 0,
                "qtde_produzida_total": 0,
            }

        return {
            "qtd_ofs": int(atual.iloc[0]["qtd_ofs"] or 0),
            "qtd_apontamentos": int(apont.iloc[0]["qtd_apontamentos"] or 0),
            "qtd_of_produto": int(apont.iloc[0]["qtd_of_produto"] or 0),
            "qtde_produzida_total": float(atual.iloc[0]["qtde_produzida_total"] or 0),
        }
    except Exception:
        return {
            "qtd_ofs": 0,
            "qtd_apontamentos": 0,
            "qtd_of_produto": 0,
            "qtde_produzida_total": 0,
        }

def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])
