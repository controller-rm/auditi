import pandas as pd
import streamlit as st
from services.query_service import run_query


def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


SQL_FATURAMENTO_RESUMO = """
SELECT
    COALESCE(SUM(
        CASE
            WHEN DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
            THEN VALOR_ITEM
            ELSE 0
        END
    ), 0) AS valor_atual,

    COALESCE(SUM(
        CASE
            WHEN DATA_MOVTO_T >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_FORMAT(CURDATE(), '%Y-%m-01')
            THEN VALOR_ITEM
            ELSE 0
        END
    ), 0) AS valor_anterior,

    COALESCE(SUM(
        CASE
            WHEN CME = 210
             AND DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
            THEN VALOR_ITEM
            ELSE 0
        END
    ), 0) AS faturamento_bruto,

    COALESCE(SUM(
        CASE
            WHEN CME = 140
             AND DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
            THEN VALOR_ITEM
            ELSE 0
        END
    ), 0) AS devolucoes,

    COALESCE(SUM(
        CASE
            WHEN CME IN (210, 140)
             AND DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
            THEN VALOR_ITEM
            ELSE 0
        END
    ), 0) AS faturamento_liquido
FROM RVE520CSV2
WHERE CME IN (210, 140)
  AND DATA_MOVTO_T >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
  AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
"""


SQL_FATURAMENTO_SERIE = """
SELECT
    DATE_FORMAT(DATA_MOVTO_T, '%b') AS mes,
    MONTH(DATA_MOVTO_T) AS mes_num,
    COALESCE(SUM(VALOR_ITEM), 0) AS valor
FROM RVE520CSV2
WHERE CME IN (210, 140)
  AND YEAR(DATA_MOVTO_T) = YEAR(CURDATE())
GROUP BY DATE_FORMAT(DATA_MOVTO_T, '%b'), MONTH(DATA_MOVTO_T)
ORDER BY mes_num
"""


SQL_FATURAMENTO_POR_EMPRESA = """
SELECT
    COD_UNICO_EMP,
    COALESCE(SUM(VALOR_ITEM), 0) AS valor_faturado
FROM RVE520CSV2
WHERE CME IN (210, 140)
  AND DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
  AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
GROUP BY COD_UNICO_EMP
ORDER BY valor_faturado DESC
"""


@st.cache_data(ttl=300)
def _get_resumo_faturamento():
    return run_query(SQL_FATURAMENTO_RESUMO)


@st.cache_data(ttl=300)
def _get_faturamento_por_empresa():
    return run_query(SQL_FATURAMENTO_POR_EMPRESA)


@st.cache_data(ttl=300)
def _get_serie_mensal():
    return run_query(SQL_FATURAMENTO_SERIE)


def get_kpi():
    try:
        resumo = _get_resumo_faturamento()
        por_empresa = _get_faturamento_por_empresa()

        valor_atual = 0.0
        valor_anterior = 0.0
        faturamento_bruto = 0.0
        devolucoes = 0.0
        faturamento_liquido = 0.0

        if resumo is not None and not resumo.empty:
            linha = resumo.iloc[0]
            valor_atual = float(linha["valor_atual"] or 0)
            valor_anterior = float(linha["valor_anterior"] or 0)
            faturamento_bruto = float(linha["faturamento_bruto"] or 0)
            devolucoes = float(linha["devolucoes"] or 0)
            faturamento_liquido = float(linha["faturamento_liquido"] or 0)

        extra_linhas = [
            f"Bruto: {formatar_moeda_br(faturamento_bruto)}",
            f"Devoluções: {formatar_moeda_br(abs(devolucoes))}",
        ]

        if por_empresa is not None and not por_empresa.empty:
            extra_linhas.append("Top empresas:")
            top5 = por_empresa.head(5)

            for _, row in top5.iterrows():
                cod_emp = row["COD_UNICO_EMP"]
                valor_emp = float(row["valor_faturado"] or 0)
                extra_linhas.append(f"{cod_emp}: {formatar_moeda_br(valor_emp)}")

        extra = "<br>".join(extra_linhas)

        return {
            "nome": "Valor Faturamento Líquido Mês",
            "valor": faturamento_liquido,
            "valor_anterior": valor_anterior,
            "unidade": "R$",
            "cor": "card-green",
            "extra": extra,
        }

    except Exception as e:
        st.error(f"Erro no módulo Faturamento: {e}")
        return {
            "nome": "Valor Faturamento Líquido Mês",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-green",
            "extra": None,
        }


def get_serie_mensal():
    try:
        df = _get_serie_mensal()
        if df is None or df.empty:
            return pd.DataFrame(columns=["Mês", "Valor"])

        return df.rename(columns={"mes": "Mês", "valor": "Valor"})[["Mês", "Valor"]]

    except Exception:
        return pd.DataFrame(columns=["Mês", "Valor"])


def get_faturamento_por_empresa():
    try:
        df = _get_faturamento_por_empresa()
        if df is None or df.empty:
            return pd.DataFrame(columns=["COD_UNICO_EMP", "valor_faturado"])

        df = df.copy()
        df["valor_faturado"] = df["valor_faturado"].astype(float)
        return df

    except Exception:
        return pd.DataFrame(columns=["COD_UNICO_EMP", "valor_faturado"])
