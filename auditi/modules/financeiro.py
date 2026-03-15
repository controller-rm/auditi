import pandas as pd
import streamlit as st
from services.query_service import run_query

SQL_FIN_ATUAL = """
SELECT
    COALESCE(SUM(valor_duplicata), 0) AS total_pago,
    COALESCE(SUM(COALESCE(juros_pagos, 0)), 0) AS juros_pagos_mes
FROM DUPLICATAS_APAGAR
WHERE data_pagamento IS NOT NULL
  AND DATE(data_pagamento) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND DATE(data_pagamento) <= CURDATE()
"""

SQL_FIN_ANTERIOR = """
SELECT
    COALESCE(SUM(valor_duplicata), 0) AS total_pago
FROM DUPLICATAS_APAGAR
WHERE data_pagamento IS NOT NULL
  AND DATE(data_pagamento) >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
  AND DATE(data_pagamento) < DATE_FORMAT(CURDATE(), '%Y-%m-01')
"""

SQL_FIN_ABERTO = """
SELECT
    COALESCE(SUM(
        CASE
            WHEN COALESCE(saldo_apagar, 0) > 0
             AND DATE(data_vencimento) < CURDATE()
            THEN saldo_apagar
            ELSE 0
        END
    ), 0) AS total_vencido,

    COALESCE(SUM(
        CASE
            WHEN COALESCE(saldo_apagar, 0) > 0
             AND DATE(data_vencimento) >= CURDATE()
            THEN saldo_apagar
            ELSE 0
        END
    ), 0) AS total_a_vencer,

    COUNT(
        CASE
            WHEN COALESCE(saldo_apagar, 0) > 0
             AND DATE(data_vencimento) < CURDATE()
            THEN 1
        END
    ) AS qtd_titulos_vencidos,

    COUNT(
        CASE
            WHEN COALESCE(saldo_apagar, 0) > 0
             AND DATE(data_vencimento) >= CURDATE()
            THEN 1
        END
    ) AS qtd_titulos_a_vencer
FROM DUPLICATAS_APAGAR
"""

def get_kpi():
    try:
        atual = run_query(SQL_FIN_ATUAL)
        anterior = run_query(SQL_FIN_ANTERIOR)
        aberto = run_query(SQL_FIN_ABERTO)

        return {
            "nome": "Total Pago Mês",
            "valor": float(atual.iloc[0]["total_pago"] or 0),
            "valor_anterior": float(anterior.iloc[0]["total_pago"] or 0),
            "unidade": "R$",
            "cor": "card-blue",
            "juros_pagos_mes": float(atual.iloc[0]["juros_pagos_mes"] or 0),
            "total_vencido": float(aberto.iloc[0]["total_vencido"] or 0),
            "total_a_vencer": float(aberto.iloc[0]["total_a_vencer"] or 0),
            "qtd_titulos_vencidos": int(aberto.iloc[0]["qtd_titulos_vencidos"] or 0),
            "qtd_titulos_a_vencer": int(aberto.iloc[0]["qtd_titulos_a_vencer"] or 0),
        }

    except Exception as e:
        st.error(f"Erro no módulo Financeiro: {e}")
        return {
            "nome": "Total Pago Mês",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-blue",
            "juros_pagos_mes": 0,
            "total_vencido": 0,
            "total_a_vencer": 0,
            "qtd_titulos_vencidos": 0,
            "qtd_titulos_a_vencer": 0,
        }

def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])