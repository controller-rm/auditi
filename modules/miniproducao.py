import pandas as pd
import streamlit as st
from services.query_service import run_query


SQL_MINIPRODUCAO = """
WITH horas_base AS (
    SELECT DISTINCT
        TRIM(ht.nro_of) AS nro_of,
        DATE(ht.data_abertura) AS data_abertura,
        SUBSTRING_INDEX(TRIM(ht.produto), ' ', 1) AS cod_produto
    FROM HORAS_TRAB ht
    WHERE TRIM(ht.equipamento) = '100'
      AND ht.data_abertura IS NOT NULL
      AND TRIM(ht.nro_of) <> ''
),
ordem_base AS (
    SELECT
        TRIM(ofa.nro_of) AS nro_of,
        SUBSTRING_INDEX(TRIM(ofa.produto), ' ', 1) AS cod_produto,
        MAX(COALESCE(ofa.qtde, 0)) AS qtde
    FROM ORDEM_FABRIC ofa
    WHERE TRIM(ofa.nro_of) <> ''
    GROUP BY
        TRIM(ofa.nro_of),
        SUBSTRING_INDEX(TRIM(ofa.produto), ' ', 1)
),
base_final AS (
    SELECT
        hb.nro_of,
        hb.data_abertura,
        hb.cod_produto,
        COALESCE(ob.qtde, 0) AS qtde
    FROM horas_base hb
    LEFT JOIN ordem_base ob
        ON hb.nro_of = ob.nro_of
       AND hb.cod_produto = ob.cod_produto
)
SELECT
    COUNT(DISTINCT CASE
        WHEN YEAR(data_abertura) = YEAR(CURDATE())
         AND MONTH(data_abertura) = MONTH(CURDATE())
        THEN nro_of
    END) AS qtd_mes_atual,

    COUNT(DISTINCT CASE
        WHEN YEAR(data_abertura) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
         AND MONTH(data_abertura) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
        THEN nro_of
    END) AS qtd_mes_anterior,

    COUNT(DISTINCT CASE
        WHEN YEAR(data_abertura) = YEAR(CURDATE())
        THEN nro_of
    END) AS qtd_acumulado_ano,

    SUM(CASE
        WHEN YEAR(data_abertura) = YEAR(CURDATE())
         AND MONTH(data_abertura) = MONTH(CURDATE())
        THEN qtde
        ELSE 0
    END) AS qtde_mes_atual,

    SUM(CASE
        WHEN YEAR(data_abertura) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
         AND MONTH(data_abertura) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))
        THEN qtde
        ELSE 0
    END) AS qtde_mes_anterior,

    SUM(CASE
        WHEN YEAR(data_abertura) = YEAR(CURDATE())
        THEN qtde
        ELSE 0
    END) AS qtde_acumulado_ano
FROM base_final
"""


SQL_MINIPRODUCAO_MENSAL = """
WITH horas_base AS (
    SELECT DISTINCT
        TRIM(ht.nro_of) AS nro_of,
        DATE(ht.data_abertura) AS data_abertura,
        SUBSTRING_INDEX(TRIM(ht.produto), ' ', 1) AS cod_produto
    FROM HORAS_TRAB ht
    WHERE TRIM(ht.equipamento) = '100'
      AND ht.data_abertura IS NOT NULL
      AND TRIM(ht.nro_of) <> ''
),
ordem_base AS (
    SELECT
        TRIM(ofa.nro_of) AS nro_of,
        SUBSTRING_INDEX(TRIM(ofa.produto), ' ', 1) AS cod_produto,
        MAX(COALESCE(ofa.qtde, 0)) AS qtde
    FROM ORDEM_FABRIC ofa
    WHERE TRIM(ofa.nro_of) <> ''
    GROUP BY
        TRIM(ofa.nro_of),
        SUBSTRING_INDEX(TRIM(ofa.produto), ' ', 1)
),
base_final AS (
    SELECT
        hb.nro_of,
        hb.data_abertura,
        hb.cod_produto,
        COALESCE(ob.qtde, 0) AS qtde
    FROM horas_base hb
    LEFT JOIN ordem_base ob
        ON hb.nro_of = ob.nro_of
       AND hb.cod_produto = ob.cod_produto
)
SELECT
    DATE_FORMAT(data_abertura, '%m/%Y') AS mes_ref,
    COUNT(DISTINCT nro_of) AS qtd_ofs,
    SUM(qtde) AS qtde_total
FROM base_final
WHERE YEAR(data_abertura) = YEAR(CURDATE())
GROUP BY DATE_FORMAT(data_abertura, '%m/%Y')
ORDER BY MIN(data_abertura)
"""


@st.cache_data(ttl=300)
def get_kpi():
    try:
        df = run_query(SQL_MINIPRODUCAO)

        if df.empty:
            return {
                "nome": "Mini Produção",
                "valor": 0,
                "valor_anterior": 0,
                "unidade": "",
                "cor": "card-blue",
                "extra": "Sem dados para o período",
                "qtd_mes_atual": 0,
                "qtd_mes_anterior": 0,
                "qtd_acumulado_ano": 0,
                "qtde_mes_atual": 0,
                "qtde_mes_anterior": 0,
                "qtde_acumulado_ano": 0,
            }

        row = df.iloc[0].fillna(0)

        qtd_mes_atual = int(row.get("qtd_mes_atual", 0) or 0)
        qtd_mes_anterior = int(row.get("qtd_mes_anterior", 0) or 0)
        qtd_acumulado_ano = int(row.get("qtd_acumulado_ano", 0) or 0)

        qtde_mes_atual = float(row.get("qtde_mes_atual", 0) or 0)
        qtde_mes_anterior = float(row.get("qtde_mes_anterior", 0) or 0)
        qtde_acumulado_ano = float(row.get("qtde_acumulado_ano", 0) or 0)

        return {
            "nome": "Mini Produção",
            "valor": qtd_mes_atual,
            "valor_anterior": qtd_mes_anterior,
            "unidade": "",
            "cor": "card-blue",
            "extra": (
                f"Mês ant.: {qtd_mes_anterior} OFs<br>"
                f"Acum. ano: {qtd_acumulado_ano} OFs<br>"
                f"Qtde mês ant.: {qtde_mes_anterior:,.0f}<br>"
                f"Qtde mês: {qtde_mes_atual:,.0f}<br>"
                f"Qtde ano: {qtde_acumulado_ano:,.0f}"
            ).replace(",", "."),
            "qtd_mes_atual": qtd_mes_atual,
            "qtd_mes_anterior": qtd_mes_anterior,
            "qtd_acumulado_ano": qtd_acumulado_ano,
            "qtde_mes_atual": qtde_mes_atual,
            "qtde_mes_anterior": qtde_mes_anterior,
            "qtde_acumulado_ano": qtde_acumulado_ano,
            "extra_obs": "Considerando apenas apontamento MINI PRODUCAO"
        }

    except Exception as e:
        return {
            "nome": "Mini Produção",
            "valor": qtd_mes_atual,
            "valor_anterior": qtd_mes_anterior,
            "unidade": "",
            "cor": "card-blue",
            "extra": (
                f"Qtde mês: {qtde_mes_atual:,.0f}<br>"
                f"Mês ant.: {qtd_mes_anterior} OFs<br>"
                f"Qtde mês ant.: {qtde_mes_anterior:,.0f}<br>"
                f"Acum. ano: {qtd_acumulado_ano} OFs<br>"
                f"Qtde ano: {qtde_acumulado_ano:,.0f}"
            ).replace(",", "."),
            "qtd_mes_atual": qtd_mes_atual,
            "qtd_mes_anterior": qtd_mes_anterior,
            "qtd_acumulado_ano": qtd_acumulado_ano,
            "qtde_mes_atual": qtde_mes_atual,
            "qtde_mes_anterior": qtde_mes_anterior,
            "qtde_acumulado_ano": qtde_acumulado_ano,
        }


@st.cache_data(ttl=300)
def get_df_mensal():
    try:
        df = run_query(SQL_MINIPRODUCAO_MENSAL)
        if df.empty:
            return pd.DataFrame(columns=["mes_ref", "qtd_ofs", "qtde_total"])
        return df
    except Exception:
        return pd.DataFrame(columns=["mes_ref", "qtd_ofs", "qtde_total"])
