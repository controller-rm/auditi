import pandas as pd
import streamlit as st
from services.query_service import run_query


def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


SQL_PEDIDOS_ATUAL = """
SELECT
    COUNT(DISTINCT a.nro_pedido) AS qtd_pedidos,
    COALESCE(SUM(
        GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) * i.preco_unitario
    ), 0) AS valor_pedidos_pendentes
FROM PEDIDO a
INNER JOIN ITENS_PEDIDO i
    ON a.nro_pedido = i.nro_pedido
   AND a.codigo_filial = i.codigo_filial
WHERE DATE(a.data_pedido) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND DATE(a.data_pedido) <= CURDATE()
  AND a.situacao_pedido NOT IN (8, 9)
  AND i.situacao_item NOT IN (3, 9)
  AND i.cme = 210
  AND GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) > 0
"""

SQL_PEDIDOS_ANTERIOR = """
SELECT
    COUNT(DISTINCT a.nro_pedido) AS qtd_pedidos,
    COALESCE(SUM(
        GREATEST(i.quantidade_pedida - i.quantidade_atendida, 0) * i.preco_unitario
    ), 0) AS valor_pedidos_pendentes
FROM PEDIDO a
INNER JOIN ITENS_PEDIDO i
    ON a.nro_pedido = i.nro_pedido
   AND a.codigo_filial = i.codigo_filial
WHERE DATE(a.data_pedido) >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
  AND DATE(a.data_pedido) < DATE_FORMAT(CURDATE(), '%Y-%m-01')
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

SQL_PRAZO_MEDIO_ATUAL = """
SELECT
    a.nro_pedido,
    GREATEST(DATEDIFF(DATE(a.data_nf), DATE(a.data_pedido)), 0) AS prazo_dias
FROM PEDIDO a
WHERE DATE(a.data_pedido) >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND DATE(a.data_pedido) <= CURDATE()
  AND a.data_nf IS NOT NULL
  AND a.data_pedido IS NOT NULL
  AND a.situacao_pedido NOT IN (8, 9)
"""

SQL_PRAZO_MEDIO_ANTERIOR = """
SELECT
    a.nro_pedido,
    GREATEST(DATEDIFF(DATE(a.data_nf), DATE(a.data_pedido)), 0) AS prazo_dias
FROM PEDIDO a
WHERE DATE(a.data_pedido) >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
  AND DATE(a.data_pedido) < DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND a.data_nf IS NOT NULL
  AND a.data_pedido IS NOT NULL
  AND a.situacao_pedido NOT IN (8, 9)
"""


def get_kpi():
    try:
        atual = run_query(SQL_PEDIDOS_ATUAL)
        anterior = run_query(SQL_PEDIDOS_ANTERIOR)
        por_empresa = run_query(SQL_PEDIDOS_POR_EMPRESA)

        valor_atual = float(atual.iloc[0]["valor_pedidos_pendentes"] or 0)
        valor_anterior = float(anterior.iloc[0]["valor_pedidos_pendentes"] or 0)
        qtd_pedidos = int(atual.iloc[0]["qtd_pedidos"] or 0)
        qtd_pedidos_anterior = int(anterior.iloc[0]["qtd_pedidos"] or 0)

        extra = f"{qtd_pedidos} pedidos no mês"

        if por_empresa is not None and not por_empresa.empty:
            linhas = []
            for _, row in por_empresa.head(5).iterrows():
                cod_emp = row["cod_unico_emp"]
                valor_emp = float(row["valor_pedidos_pendentes"] or 0)
                linhas.append(f"{cod_emp}: {formatar_moeda_br(valor_emp)}")

            if linhas:
                extra += "<br>" + "<br>".join(linhas)

        return {
            "nome": "Total de Pedidos Pend. Mês",
            "valor": valor_atual,
            "valor_anterior": valor_anterior,
            "unidade": "R$",
            "cor": "card-yellow",
            "qtd_pedidos": qtd_pedidos,
            "qtd_pedidos_anterior": qtd_pedidos_anterior,
            "extra": extra,
        }

    except Exception as e:
        st.error(f"Erro no módulo Pedidos Mês: {e}")
        return {
            "nome": "Total de Pedidos Pend. Mês",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-yellow",
            "qtd_pedidos": 0,
            "qtd_pedidos_anterior": 0,
            "extra": None,
        }


def get_kpi_prazo_medio_entrega():
    try:
        atual = run_query(SQL_PRAZO_MEDIO_ATUAL)
        anterior = run_query(SQL_PRAZO_MEDIO_ANTERIOR)

        if atual is None or atual.empty:
            atual = pd.DataFrame(columns=["nro_pedido", "prazo_dias"])

        if anterior is None or anterior.empty:
            anterior = pd.DataFrame(columns=["nro_pedido", "prazo_dias"])

        atual["prazo_dias"] = pd.to_numeric(atual["prazo_dias"], errors="coerce").fillna(0)
        anterior["prazo_dias"] = pd.to_numeric(anterior["prazo_dias"], errors="coerce").fillna(0)

        prazo_medio_atual = float(atual["prazo_dias"].mean()) if not atual.empty else 0.0
        prazo_medio_anterior = float(anterior["prazo_dias"].mean()) if not anterior.empty else 0.0

        qtd_ate_2 = int((atual["prazo_dias"] <= 2).sum()) if not atual.empty else 0
        qtd_ate_5 = int(((atual["prazo_dias"] > 2) & (atual["prazo_dias"] <= 5)).sum()) if not atual.empty else 0
        qtd_ate_8 = int(((atual["prazo_dias"] > 5) & (atual["prazo_dias"] <= 8)).sum()) if not atual.empty else 0
        qtd_maior_8 = int((atual["prazo_dias"] > 8).sum()) if not atual.empty else 0

        return {
            "nome": "Prazo Médio Faturamento",
            "valor": prazo_medio_atual,
            "valor_anterior": prazo_medio_anterior,
            "unidade": "dias",
            "cor": "card-blue",
            "qtd_ate_2": qtd_ate_2,
            "qtd_ate_5": qtd_ate_5,
            "qtd_ate_8": qtd_ate_8,
            "qtd_maior_8": qtd_maior_8,
            "qtd_pedidos_faturados": int(len(atual)),
            "extra": (
                f"Até 2d: {qtd_ate_2} | "
                f"Até 5d: {qtd_ate_5}<br>"
                f"Até 8d: {qtd_ate_8} | "
                f">8d: {qtd_maior_8}"
            )
        }

    except Exception as e:
        st.error(f"Erro no KPI de Prazo Médio de Entrega: {e}")
        return {
            "nome": "Prazo Médio Faturamento",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "dias",
            "cor": "card-blue",
            "qtd_ate_2": 0,
            "qtd_ate_5": 0,
            "qtd_ate_8": 0,
            "qtd_maior_8": 0,
            "qtd_pedidos_faturados": 0,
            "extra": "Até 2d: 0 | Até 5d: 0<br>Até 8d: 0 | >8d: 0"
        }


def get_pedidos_por_empresa():
    try:
        df = run_query(SQL_PEDIDOS_POR_EMPRESA)

        if df is None or df.empty:
            return pd.DataFrame(columns=["cod_unico_emp", "valor_pedidos_pendentes"])

        df["valor_pedidos_pendentes"] = pd.to_numeric(
            df["valor_pedidos_pendentes"], errors="coerce"
        ).fillna(0)

        return df

    except Exception:
        return pd.DataFrame(columns=["cod_unico_emp", "valor_pedidos_pendentes"])


def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])