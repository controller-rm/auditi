import pandas as pd
import streamlit as st
from services.query_service import run_query


SQL_MARGEM_ATUAL = """
SELECT
    COALESCE(SUM(VALOR_MARGEM_ATI), 0) AS total_margem_mes,
    COALESCE(SUM(VALOR_ITEM), 0) AS total_faturamento_mes
FROM RVE520CSV2
WHERE CME = 210
  AND DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
"""

SQL_MARGEM_ANTERIOR = """
SELECT
    COALESCE(SUM(VALOR_MARGEM_ATI), 0) AS total_margem_mes_anterior,
    COALESCE(SUM(VALOR_ITEM), 0) AS total_faturamento_mes_anterior
FROM RVE520CSV2
WHERE CME = 210
  AND DATA_MOVTO_T >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
  AND DATA_MOVTO_T < DATE_FORMAT(CURDATE(), '%Y-%m-01')
"""

SQL_MARGEM_ULTIMO_DIA = """
SELECT
    COALESCE(SUM(VALOR_MARGEM_ATI), 0) AS total_margem_ultimo_dia,
    MAX(DATA_MOVTO_T) AS data_ultimo_dia
FROM RVE520CSV2
WHERE CME = 210
  AND DATA_MOVTO_T = (
      SELECT MAX(DATA_MOVTO_T)
      FROM RVE520CSV2
      WHERE CME = 210
        AND DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
        AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
  )
"""


def get_kpi():
    try:
        atual = run_query(SQL_MARGEM_ATUAL)
        anterior = run_query(SQL_MARGEM_ANTERIOR)
        ultimo_dia = run_query(SQL_MARGEM_ULTIMO_DIA)

        total_margem_mes = float(atual.iloc[0]["total_margem_mes"] or 0)
        total_faturamento_mes = float(atual.iloc[0]["total_faturamento_mes"] or 0)

        total_margem_mes_anterior = float(anterior.iloc[0]["total_margem_mes_anterior"] or 0)
        total_faturamento_mes_anterior = float(anterior.iloc[0]["total_faturamento_mes_anterior"] or 0)

        total_margem_ultimo_dia = float(ultimo_dia.iloc[0]["total_margem_ultimo_dia"] or 0)
        data_ultimo_dia = ultimo_dia.iloc[0]["data_ultimo_dia"]

        percentual_mes = (total_margem_mes / total_faturamento_mes * 100) if total_faturamento_mes else 0
        percentual_mes_anterior = (
            total_margem_mes_anterior / total_faturamento_mes_anterior * 100
        ) if total_faturamento_mes_anterior else 0

        data_ultimo_dia_formatada = ""
        if pd.notna(data_ultimo_dia):
            data_ultimo_dia_formatada = pd.to_datetime(data_ultimo_dia).strftime("%d/%m/%Y")

        return {
            "nome": "Margem",
            "valor": percentual_mes,
            "valor_anterior": percentual_mes_anterior,
            "unidade": "%",
            "cor": "card-blue",
            "total_margem_mes": total_margem_mes,
            "total_margem_mes_anterior": total_margem_mes_anterior,
            "total_margem_ultimo_dia": total_margem_ultimo_dia,
            "data_ultimo_dia": data_ultimo_dia_formatada,
            "extra_obs": "Esse Card Apresenta o Valor da Margem acumulada mês e valores da Margem"
        }

    except Exception as e:
        st.error(f"Erro no módulo Margem: {e}")
        return {
            "nome": "Margem",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "%",
            "cor": "card-blue",
            "total_margem_mes": 0,
            "total_margem_mes_anterior": 0,
            "total_margem_ultimo_dia": 0,
            "data_ultimo_dia": "",
        }


def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])
