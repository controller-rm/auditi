import pandas as pd
import streamlit as st
from services.query_service import run_query

SQL_ARECEBER_ATUAL = """
SELECT

    /* TOTAL RECEBIDO NO MÊS */
    COALESCE(SUM(
        CASE
            WHEN dup_ja_rec_data_recebimento IS NOT NULL
             AND DATE(dup_ja_rec_data_recebimento) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATE(dup_ja_rec_data_recebimento) <= CURDATE()
            THEN COALESCE(valor_duplicata,0)
            ELSE 0
        END
    ),0) AS total_recebido_mes,


    /* TOTAL EM ABERTO */
    COALESCE(SUM(
        CASE
            WHEN COALESCE(saldo_duplicata,0) > 0
            THEN saldo_duplicata
            ELSE 0
        END
    ),0) AS valor_a_receber,


    /* QTD TITULOS EM ABERTO */
    COUNT(
        CASE
            WHEN COALESCE(saldo_duplicata,0) > 0
            THEN 1
        END
    ) AS qtd_titulos,


    /* DESCONTO CONCEDIDO NO MÊS */
    COALESCE(SUM(
        CASE
            WHEN dup_ja_rec_data_recebimento IS NOT NULL
             AND DATE(dup_ja_rec_data_recebimento) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATE(dup_ja_rec_data_recebimento) <= CURDATE()
            THEN COALESCE(dup_ja_rec_desconto_concedido,0)
            ELSE 0
        END
    ),0) AS desconto_concedido_mes,


    /* JUROS COBRADOS NO MÊS */
    COALESCE(SUM(
        CASE
            WHEN dup_ja_rec_data_recebimento IS NOT NULL
             AND DATE(dup_ja_rec_data_recebimento) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATE(dup_ja_rec_data_recebimento) <= CURDATE()
            THEN COALESCE(dup_ja_rec_juros_cobrado,0)
            ELSE 0
        END
    ),0) AS juros_cobrado_mes,


    /* TOTAL VENCIDO */
    COALESCE(SUM(
        CASE
            WHEN COALESCE(saldo_duplicata,0) > 0
             AND DATE(data_vencimento) < CURDATE()
            THEN saldo_duplicata
            ELSE 0
        END
    ),0) AS valor_vencido,


    COUNT(
        CASE
            WHEN COALESCE(saldo_duplicata,0) > 0
             AND DATE(data_vencimento) < CURDATE()
            THEN 1
        END
    ) AS qtd_titulos_vencidos,


    /* TOTAL A VENCER */
    COALESCE(SUM(
        CASE
            WHEN COALESCE(saldo_duplicata,0) > 0
             AND DATE(data_vencimento) >= CURDATE()
            THEN saldo_duplicata
            ELSE 0
        END
    ),0) AS valor_a_vencer,


    COUNT(
        CASE
            WHEN COALESCE(saldo_duplicata,0) > 0
             AND DATE(data_vencimento) >= CURDATE()
            THEN 1
        END
    ) AS qtd_titulos_a_vencer


FROM DUPLICATAS_RECEBER
"""

SQL_ARECEBER_ANTERIOR = """
SELECT
    COALESCE(SUM(
        CASE
            WHEN dup_ja_rec_data_recebimento IS NOT NULL
             AND DATE(dup_ja_rec_data_recebimento) >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
             AND DATE(dup_ja_rec_data_recebimento) < DATE_FORMAT(CURDATE(), '%Y-%m-01')
            THEN COALESCE(valor_duplicata, 0)
            ELSE 0
        END
    ), 0) AS total_recebido_mes
FROM DUPLICATAS_RECEBER
"""

SQL_SERIE_MENSAL = """
SELECT
    DATE_FORMAT(dup_ja_rec_data_recebimento, '%Y-%m') AS mes_ordem,
    DATE_FORMAT(dup_ja_rec_data_recebimento, '%m/%Y') AS mes,
    COALESCE(SUM(valor_duplicata), 0) AS valor
FROM DUPLICATAS_RECEBER
WHERE dup_ja_rec_data_recebimento IS NOT NULL
GROUP BY DATE_FORMAT(dup_ja_rec_data_recebimento, '%Y-%m'),
         DATE_FORMAT(dup_ja_rec_data_recebimento, '%m/%Y')
ORDER BY mes_ordem
"""

def get_kpi():
    try:
        atual = run_query(SQL_ARECEBER_ATUAL)
        anterior = run_query(SQL_ARECEBER_ANTERIOR)

        linha_atual = atual.iloc[0]
        linha_anterior = anterior.iloc[0]

        return {
            "nome": "Total Recebido Mês",
            "valor": float(linha_atual["total_recebido_mes"] or 0),
            "valor_anterior": float(linha_anterior["total_recebido_mes"] or 0),
            "unidade": "R$",
            "cor": "card-green",
            "valor_a_receber": float(linha_atual["valor_a_receber"] or 0),
            "qtd_titulos": int(linha_atual["qtd_titulos"] or 0),
            "desconto_concedido_mes": float(linha_atual["desconto_concedido_mes"] or 0),
            "juros_cobrado_mes": float(linha_atual["juros_cobrado_mes"] or 0),
            "valor_vencido": float(linha_atual["valor_vencido"] or 0),
            "qtd_titulos_vencidos": int(linha_atual["qtd_titulos_vencidos"] or 0),
            "valor_a_vencer": float(linha_atual["valor_a_vencer"] or 0),
            "qtd_titulos_a_vencer": int(linha_atual["qtd_titulos_a_vencer"] or 0),
        }

    except Exception as e:
        st.error(f"Erro no módulo A Receber: {e}")
        return {
            "nome": "Total Recebido Mês",
            "valor": 0.0,
            "valor_anterior": 0.0,
            "unidade": "R$",
            "cor": "card-green",
            "valor_a_receber": 0.0,
            "qtd_titulos": 0,
            "desconto_concedido_mes": 0.0,
            "juros_cobrado_mes": 0.0,
            "valor_vencido": 0.0,
            "qtd_titulos_vencidos": 0,
            "valor_a_vencer": 0.0,
            "qtd_titulos_a_vencer": 0,
        }

def get_serie_mensal():
    try:
        df = run_query(SQL_SERIE_MENSAL)

        if df is None or df.empty:
            return pd.DataFrame(columns=["Mês", "Valor"])

        df = df.rename(columns={
            "mes": "Mês",
            "valor": "Valor"
        })

        return df[["Mês", "Valor"]]

    except Exception as e:
        st.error(f"Erro ao carregar série mensal do A Receber: {e}")
        return pd.DataFrame(columns=["Mês", "Valor"])