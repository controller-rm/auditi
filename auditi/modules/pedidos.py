import pandas as pd
import streamlit as st
from services.query_service import run_query


def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


SQL_PEDIDOS_ATUAL = """
SELECT
    COALESCE(SUM(
        GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) * i.preco_unitario
    ), 0) AS valor_pedidos_pendentes
FROM PEDIDO a
INNER JOIN ITENS_PEDIDO i
    ON a.nro_pedido = i.nro_pedido
   AND a.codigo_filial = i.codigo_filial
WHERE DATE(a.data_pedido) <= CURDATE()
  AND a.situacao_pedido NOT IN (8, 9)
  AND i.situacao_item NOT IN (3, 9)
  AND i.cme = 210
  AND GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) > 0
"""

SQL_PEDIDOS_ANTERIOR = """
SELECT
    COALESCE(SUM(
        GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) * i.preco_unitario
    ), 0) AS valor_pedidos_pendentes
FROM PEDIDO a
INNER JOIN ITENS_PEDIDO i
    ON a.nro_pedido = i.nro_pedido
   AND a.codigo_filial = i.codigo_filial
WHERE DATE(a.data_pedido) < DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND a.situacao_pedido NOT IN (8, 9)
  AND i.situacao_item NOT IN (3, 9)
  AND i.cme = 210
  AND GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) > 0
"""

SQL_PEDIDOS_POR_EMPRESA = """
SELECT
    a.cod_unico_emp,
    COALESCE(SUM(
        GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) * i.preco_unitario
    ), 0) AS valor_pedidos_pendentes
FROM PEDIDO a
INNER JOIN ITENS_PEDIDO i
    ON a.nro_pedido = i.nro_pedido
   AND a.codigo_filial = i.codigo_filial
WHERE DATE(a.data_pedido) <= CURDATE()
  AND a.situacao_pedido NOT IN (8, 9)
  AND i.situacao_item NOT IN (3, 9)
  AND i.cme = 210
  AND GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) > 0
GROUP BY a.cod_unico_emp
ORDER BY valor_pedidos_pendentes DESC
"""


def get_kpi():
    try:
        atual = run_query(SQL_PEDIDOS_ATUAL)
        anterior = run_query(SQL_PEDIDOS_ANTERIOR)
        por_empresa = run_query(SQL_PEDIDOS_POR_EMPRESA)

        valor_atual = float(atual.iloc[0]["valor_pedidos_pendentes"] or 0)
        valor_anterior = float(anterior.iloc[0]["valor_pedidos_pendentes"] or 0)

        extra = None
        if por_empresa is not None and not por_empresa.empty:
            linhas = []

            for _, row in por_empresa.head(5).iterrows():
                cod_emp = row["cod_unico_emp"]
                valor_emp = float(row["valor_pedidos_pendentes"] or 0)

                linhas.append(
                    f"{cod_emp}: {formatar_moeda_br(valor_emp)}"
                )

            extra = "<br>".join(linhas)

        return {
            "nome": "Pedidos Pendentes",
            "valor": valor_atual,
            "valor_anterior": valor_anterior,
            "unidade": "R$",
            "cor": "card-yellow",
            "extra": extra,
        }

    except Exception as e:
        st.error(f"Erro no módulo Pedidos: {e}")
        return {
            "nome": "Pedidos Pendentes",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-yellow",
            "extra": None,
        }


def get_pedidos_por_empresa():
    try:
        df = run_query(SQL_PEDIDOS_POR_EMPRESA)

        if df is None or df.empty:
            return pd.DataFrame(columns=["cod_unico_emp", "valor_pedidos_pendentes"])

        df["valor_pedidos_pendentes"] = df["valor_pedidos_pendentes"].astype(float)
        return df

    except Exception:
        return pd.DataFrame(columns=["cod_unico_emp", "valor_pedidos_pendentes"])


def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])