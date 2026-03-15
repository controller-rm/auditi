import pandas as pd
import streamlit as st
from services.query_service import run_query


SQL_REPOSICAO_X_MEDIO = """
SELECT
    p.codigo_produto_material AS produto,
    p.tipo_material,
    p.valor_reposicao,
    pea.quantidade,
    pea.custo_unitario,
    pea.data_ult_compra
FROM PRODUTO p
LEFT JOIN POSICAO_ESTOQUE_ATUAL pea
    ON pea.produto = p.codigo_produto_material
WHERE p.tipo_material = 'MP'
"""


def _to_float(valor):
    if pd.isna(valor):
        return 0.0
    try:
        return float(valor)
    except Exception:
        try:
            return float(str(valor).replace(".", "").replace(",", "."))
        except Exception:
            return 0.0


def _to_datetime(valor):
    try:
        return pd.to_datetime(valor, errors="coerce")
    except Exception:
        return pd.NaT


def _classificar_faixa(diferenca_percentual):
    if pd.isna(diferenca_percentual):
        return "Sem base"

    if diferenca_percentual < -10:
        return "Reposição muito abaixo do custo médio"
    elif -10 <= diferenca_percentual < -5:
        return "Reposição abaixo"
    elif -5 <= diferenca_percentual <= 5:
        return "Faixa normal"
    elif 5 < diferenca_percentual <= 10:
        return "Reposição acima"
    elif diferenca_percentual > 10:
        return "Reposição muito acima"

    return "Sem base"


def carregar_dados():
    df = run_query(SQL_REPOSICAO_X_MEDIO)

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    for col in ["quantidade", "custo_unitario", "valor_reposicao"]:
        if col in df.columns:
            df[col] = df[col].apply(_to_float)

    if "produto" in df.columns:
        df["produto"] = df["produto"].astype(str).str.strip()

    if "tipo_material" in df.columns:
        df["tipo_material"] = (
            df["tipo_material"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

    if "data_ult_compra" in df.columns:
        df["data_ult_compra"] = df["data_ult_compra"].apply(_to_datetime)

    # Se não houver posição no estoque, assume zero
    df["quantidade"] = df["quantidade"].fillna(0)
    df["custo_unitario"] = df["custo_unitario"].fillna(0)
    df["valor_reposicao"] = df["valor_reposicao"].fillna(0)

    # Flags de validação
    df["quantidade_zero"] = df["quantidade"].round(4) <= 0
    df["reposicao_zero"] = df["valor_reposicao"].round(2) <= 0
    df["sem_valor_reposicao"] = df["reposicao_zero"]

    # Regra 1:
    # produto MP com quantidade zero e sem valor de reposição
    df["regra_sem_reposicao"] = df["quantidade_zero"] & df["reposicao_zero"]

    # Regra 2:
    # análise de faixas somente para quem tem quantidade > 0 e valores válidos
    df["base_analise_faixa"] = (
        (df["quantidade"] > 0) &
        (df["custo_unitario"] > 0) &
        (df["valor_reposicao"] > 0)
    )

    df["diferenca_percentual"] = pd.NA
    mask = df["base_analise_faixa"]

    df.loc[mask, "diferenca_percentual"] = (
        (
            df.loc[mask, "valor_reposicao"] -
            df.loc[mask, "custo_unitario"]
        ) / df.loc[mask, "custo_unitario"]
    ) * 100

    df["classificacao_reposicao"] = df["diferenca_percentual"].apply(_classificar_faixa)

    return df


def get_base_sem_reposicao():
    df = carregar_dados()

    if df.empty:
        return pd.DataFrame()

    return df[df["regra_sem_reposicao"]].copy()


def get_base_analise_reposicao():
    df = carregar_dados()

    if df.empty:
        return pd.DataFrame()

    return df[df["base_analise_faixa"]].copy()


def get_produtos_sem_reposicao():
    df = get_base_sem_reposicao()

    if df.empty:
        return pd.DataFrame(columns=[
            "produto",
            "tipo_material",
            "quantidade",
            "custo_unitario",
            "valor_reposicao",
            "data_ult_compra",
            "quantidade_zero",
            "reposicao_zero",
            "regra_sem_reposicao",
        ])

    colunas = [
        "produto",
        "tipo_material",
        "quantidade",
        "custo_unitario",
        "valor_reposicao",
        "data_ult_compra",
        "quantidade_zero",
        "reposicao_zero",
        "regra_sem_reposicao",
    ]
    return df[colunas].sort_values(by=["produto"])


def get_produtos_reposicao_muito_acima():
    df = get_base_analise_reposicao()

    if df.empty:
        return pd.DataFrame(columns=[
            "produto",
            "tipo_material",
            "quantidade",
            "custo_unitario",
            "valor_reposicao",
            "diferenca_percentual",
            "classificacao_reposicao",
            "data_ult_compra",
        ])

    df = df[df["classificacao_reposicao"] == "Reposição muito acima"].copy()

    colunas = [
        "produto",
        "tipo_material",
        "quantidade",
        "custo_unitario",
        "valor_reposicao",
        "diferenca_percentual",
        "classificacao_reposicao",
        "data_ult_compra",
    ]
    return df[colunas].sort_values(
        by=["diferenca_percentual", "produto"],
        ascending=[False, True]
    )


def get_resumo_faixas():
    df = get_base_analise_reposicao()

    ordem = [
        "Reposição muito abaixo do custo médio",
        "Reposição abaixo",
        "Faixa normal",
        "Reposição acima",
        "Reposição muito acima",
        "Sem base",
    ]

    if df.empty:
        return pd.DataFrame({
            "classificacao_reposicao": ordem,
            "qtd_produtos": [0, 0, 0, 0, 0, 0]
        })

    resumo = (
        df.groupby("classificacao_reposicao", as_index=False)
        .agg(qtd_produtos=("produto", "count"))
    )

    base = pd.DataFrame({"classificacao_reposicao": ordem})
    resumo = base.merge(resumo, on="classificacao_reposicao", how="left").fillna(0)
    resumo["qtd_produtos"] = resumo["qtd_produtos"].astype(int)

    return resumo


def get_resumo_validacao():
    df = carregar_dados()

    if df.empty:
        return {
            "total_produtos_mp": 0,
            "qtd_zero": 0,
            "reposicao_zero": 0,
            "qtd_zero_e_reposicao_zero": 0,
            "base_analise_faixa": 0,
        }

    return {
        "total_produtos_mp": int(len(df)),
        "qtd_zero": int(df["quantidade_zero"].sum()),
        "reposicao_zero": int(df["reposicao_zero"].sum()),
        "qtd_zero_e_reposicao_zero": int(df["regra_sem_reposicao"].sum()),
        "base_analise_faixa": int(df["base_analise_faixa"].sum()),
    }


def dataframe_para_csv_br(df: pd.DataFrame) -> bytes:
    df_export = df.copy()

    for col in df_export.columns:
        if pd.api.types.is_datetime64_any_dtype(df_export[col]):
            df_export[col] = df_export[col].dt.strftime("%d/%m/%Y")

    return df_export.to_csv(
        sep=";",
        decimal=",",
        index=False,
        encoding="utf-8-sig"
    ).encode("utf-8-sig")


def get_download_validacao():
    df = carregar_dados()

    if df.empty:
        return pd.DataFrame(columns=[
            "produto",
            "tipo_material",
            "quantidade",
            "custo_unitario",
            "valor_reposicao",
            "quantidade_zero",
            "reposicao_zero",
            "regra_sem_reposicao",
            "base_analise_faixa",
            "diferenca_percentual",
            "classificacao_reposicao",
        ])

    colunas = [
        "produto",
        "tipo_material",
        "quantidade",
        "custo_unitario",
        "valor_reposicao",
        "quantidade_zero",
        "reposicao_zero",
        "regra_sem_reposicao",
        "base_analise_faixa",
        "diferenca_percentual",
        "classificacao_reposicao",
    ]
    return df[colunas].sort_values(by=["produto"])


def get_kpi():
    try:
        df_sem_reposicao = get_base_sem_reposicao()
        df_analise = get_base_analise_reposicao()
        resumo_faixas = get_resumo_faixas()

        qtd_sem_reposicao = int(len(df_sem_reposicao))

        def qtd_faixa(nome):
            linha = resumo_faixas[resumo_faixas["classificacao_reposicao"] == nome]
            return 0 if linha.empty else int(linha.iloc[0]["qtd_produtos"])

        qtd_muito_abaixo = qtd_faixa("Reposição muito abaixo do custo médio")
        qtd_abaixo = qtd_faixa("Reposição abaixo")
        qtd_normal = qtd_faixa("Faixa normal")
        qtd_acima = qtd_faixa("Reposição acima")
        qtd_muito_acima = qtd_faixa("Reposição muito acima")

        return {
            "nome": "Nro Prod. Reposicao > 10% acima do C.M",
            "valor": qtd_muito_acima,
            "valor_anterior": 0,
            "unidade": "itens",
            "cor": "card-pink" if qtd_muito_acima > 0 else "card-yellow",
            "extra": (
                f"Nro Prod Analisado: {len(df_analise)}<br>"
                f"Qtde=0 sem reposição: {qtd_sem_reposicao}<br>"
                f"Muito abaixo de -10%: {qtd_muito_abaixo}<br>"
                f"Abaixo de -10% até -5%: {qtd_abaixo}<br>"
                f"Normal de -10% até -5%: {qtd_normal}<br>"
                f"Acima de +5% até +10%: {qtd_acima}<br>"
                f"Muito acima de +10%: {qtd_muito_acima}"
            ),
            "qtd_sem_reposicao": qtd_sem_reposicao,
            "qtd_muito_abaixo": qtd_muito_abaixo,
            "qtd_abaixo": qtd_abaixo,
            "qtd_normal": qtd_normal,
            "qtd_acima": qtd_acima,
            "qtd_muito_acima": qtd_muito_acima,
            "qtd_total_base": int(len(df_analise)),
        }

    except Exception as e:
        st.error(f"Erro no módulo Reposição x Médio: {e}")
        return {
            "nome": "Reposição x Custo Médio",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "itens",
            "cor": "card-yellow",
            "extra": (
                "Qtde=0 sem reposição: 0<br>"
                "Muito abaixo: 0 | Abaixo: 0<br>"
                "Normal: 0 | Acima: 0<br>"
                "Muito acima: 0 | Base: 0"
            ),
            "qtd_sem_reposicao": 0,
            "qtd_muito_abaixo": 0,
            "qtd_abaixo": 0,
            "qtd_normal": 0,
            "qtd_acima": 0,
            "qtd_muito_acima": 0,
            "qtd_total_base": 0,
        }


def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])