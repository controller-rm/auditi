import pandas as pd
import streamlit as st
from services.query_service import run_query

EQUIPAMENTO_PADRAO = "8000"

SQL_CQ_LIBERACAO_ATUAL = f"""
SELECT
    COALESCE(AVG(qtd_of_dia), 0) AS media_diaria,
    COALESCE(SUM(qtd_of_dia), 0) AS total_of_mes
FROM (
    SELECT
        DATE(h.data_abertura) AS dia,
        COUNT(DISTINCT CONCAT(h.nro_of, '-', h.produto)) AS qtd_of_dia
    FROM HORAS_TRAB h
    LEFT JOIN ORDEM_FABRIC o
        ON o.nro_of = h.nro_of
    WHERE h.data_abertura IS NOT NULL
      AND TRIM(CAST(h.equipamento AS CHAR)) = '{EQUIPAMENTO_PADRAO}'
      AND COALESCE(TRIM(CAST(o.origem AS CHAR)), 'SEM_ORIGEM') <> '997'
      AND DATE(h.data_abertura) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
      AND DATE(h.data_abertura) <= CURDATE()
    GROUP BY DATE(h.data_abertura)
) base
"""

SQL_CQ_LIBERACAO_ANTERIOR = f"""
SELECT
    COALESCE(AVG(qtd_of_dia), 0) AS media_diaria,
    COALESCE(SUM(qtd_of_dia), 0) AS total_of_mes
FROM (
    SELECT
        DATE(h.data_abertura) AS dia,
        COUNT(DISTINCT CONCAT(h.nro_of, '-', h.produto)) AS qtd_of_dia
    FROM HORAS_TRAB h
    LEFT JOIN ORDEM_FABRIC o
        ON o.nro_of = h.nro_of
    WHERE h.data_abertura IS NOT NULL
      AND TRIM(CAST(h.equipamento AS CHAR)) = '{EQUIPAMENTO_PADRAO}'
      AND COALESCE(TRIM(CAST(o.origem AS CHAR)), 'SEM_ORIGEM') <> '997'
      AND MONTH(h.data_abertura) = MONTH(CURDATE())
      AND YEAR(h.data_abertura) = YEAR(CURDATE()) - 1
    GROUP BY DATE(h.data_abertura)
) base
"""

def get_kpi():
    try:
        atual = run_query(SQL_CQ_LIBERACAO_ATUAL)
        anterior = run_query(SQL_CQ_LIBERACAO_ANTERIOR)

        return {
            "nome": "C.Q. Liberação",
            "valor": float(atual.iloc[0]["media_diaria"] or 0),
            "valor_anterior": float(anterior.iloc[0]["media_diaria"] or 0),
            "unidade": "num",
            "cor": "card-blue",
            "total_of_mes": int(atual.iloc[0]["total_of_mes"] or 0),
        }
    except Exception as e:
        st.error(f"Erro no módulo C.Q. Liberação: {e}")
        return {
            "nome": "C.Q. Liberação",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "num",
            "cor": "card-blue",
            "total_of_mes": 0,
        }

def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])