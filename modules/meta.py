import pandas as pd
import streamlit as st
from services.query_service import run_query


def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


SQL_META_VENDEDOR = """
SELECT
    VENDEDOR_COMPL,
    COD_UNICO_EMP,
    SUM(CASE
            WHEN DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
            THEN VALOR_ITEM
            ELSE 0
        END) AS valor_atual,
    SUM(CASE
            WHEN DATA_MOVTO_T >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_FORMAT(CURDATE(), '%Y-%m-01')
            THEN VALOR_ITEM
            ELSE 0
        END) AS valor_anterior
FROM RVE520CSV2
WHERE CME = 210
  AND DATA_MOVTO_T >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
  AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
GROUP BY VENDEDOR_COMPL, COD_UNICO_EMP
ORDER BY valor_atual DESC, valor_anterior DESC
"""

SQL_META_RESUMO = """
SELECT
    COALESCE(SUM(CASE
            WHEN DATA_MOVTO_T >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
            THEN VALOR_ITEM
            ELSE 0
        END), 0) AS valor_atual,
    COALESCE(SUM(CASE
            WHEN DATA_MOVTO_T >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
             AND DATA_MOVTO_T < DATE_FORMAT(CURDATE(), '%Y-%m-01')
            THEN VALOR_ITEM
            ELSE 0
        END), 0) AS valor_anterior
FROM RVE520CSV2
WHERE CME = 210
  AND DATA_MOVTO_T >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 1 MONTH), '%Y-%m-01')
  AND DATA_MOVTO_T < DATE_ADD(CURDATE(), INTERVAL 1 DAY)
"""


def get_kpi():
    try:
        resumo = run_query(SQL_META_RESUMO)
        detalhe = run_query(SQL_META_VENDEDOR)

        valor_atual = float(resumo.iloc[0]["valor_atual"] or 0)
        valor_anterior = float(resumo.iloc[0]["valor_anterior"] or 0)

        extra = None
        if detalhe is not None and not detalhe.empty:
            detalhe["valor_atual"] = pd.to_numeric(detalhe["valor_atual"], errors="coerce").fillna(0)
            top_vendedores = (
                detalhe.groupby("VENDEDOR_COMPL", as_index=False)["valor_atual"]
                .sum()
                .sort_values("valor_atual", ascending=False)
                .head(5)
            )

            linhas = []
            for _, row in top_vendedores.iterrows():
                vendedor = row["VENDEDOR_COMPL"] if pd.notna(row["VENDEDOR_COMPL"]) else "SEM VENDEDOR"
                valor = float(row["valor_atual"] or 0)
                linhas.append(f"{vendedor}: {formatar_moeda_br(valor)}")

            extra = "<br>".join(linhas)

        return {
            "nome": "Meta por Vendedor",
            "valor": valor_atual,
            "valor_anterior": valor_anterior,
            "unidade": "R$",
            "cor": "card-blue",
            "extra": extra,
            
        }

    except Exception as e:
        st.error(f"Erro no módulo Meta: {e}")
        return {
            "nome": "Meta por Vendedor",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-blue",
            "extra": None,
            "extra_obs": "Incluir informações sobre os valores do card."
        }


def get_meta_vendedor():
    try:
        df = run_query(SQL_META_VENDEDOR)

        if df is None or df.empty:
            return pd.DataFrame(
                columns=[
                    "VENDEDOR_COMPL",
                    "COD_UNICO_EMP",
                    "valor_atual",
                    "valor_anterior",
                    "diferenca",
                    "percentual"
                ]
            )

        df["VENDEDOR_COMPL"] = df["VENDEDOR_COMPL"].fillna("SEM VENDEDOR")
        df["COD_UNICO_EMP"] = df["COD_UNICO_EMP"].fillna("SEM FILIAL")
        df["valor_atual"] = pd.to_numeric(df["valor_atual"], errors="coerce").fillna(0.0)
        df["valor_anterior"] = pd.to_numeric(df["valor_anterior"], errors="coerce").fillna(0.0)

        df["diferenca"] = df["valor_atual"] - df["valor_anterior"]
        df["percentual"] = df.apply(
            lambda row: ((row["valor_atual"] / row["valor_anterior"]) - 1) * 100
            if row["valor_anterior"] not in [0, None] else 0,
            axis=1
        )

        df = df.sort_values(["valor_atual", "valor_anterior"], ascending=False).reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"Erro ao buscar meta por vendedor: {e}")
        return pd.DataFrame(
            columns=[
                "VENDEDOR_COMPL",
                "COD_UNICO_EMP",
                "valor_atual",
                "valor_anterior",
                "diferenca",
                "percentual"
            ]
        )


def get_meta_vendedor_grafico():
    """
    Retorna dataframe pronto para gráfico agrupado:
    vendedor | filial | periodo | valor
    """
    try:
        df = get_meta_vendedor()

        if df.empty:
            return pd.DataFrame(columns=["vendedor", "filial", "periodo", "valor"])

        atual = df[["VENDEDOR_COMPL", "COD_UNICO_EMP", "valor_atual"]].copy()
        atual["periodo"] = "Mês Atual"
        atual = atual.rename(
            columns={
                "VENDEDOR_COMPL": "vendedor",
                "COD_UNICO_EMP": "filial",
                "valor_atual": "valor"
            }
        )

        anterior = df[["VENDEDOR_COMPL", "COD_UNICO_EMP", "valor_anterior"]].copy()
        anterior["periodo"] = "Mês Anterior"
        anterior = anterior.rename(
            columns={
                "VENDEDOR_COMPL": "vendedor",
                "COD_UNICO_EMP": "filial",
                "valor_anterior": "valor"
            }
        )

        grafico = pd.concat([atual, anterior], ignore_index=True)
        grafico["label"] = grafico["vendedor"] + " | Filial " + grafico["filial"].astype(str)

        return grafico[["vendedor", "filial", "label", "periodo", "valor"]]

    except Exception as e:
        st.error(f"Erro ao montar gráfico de meta por vendedor: {e}")
        return pd.DataFrame(columns=["vendedor", "filial", "label", "periodo", "valor"])
