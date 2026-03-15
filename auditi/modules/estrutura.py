import pandas as pd
import streamlit as st
from services.query_service import run_query


SQL_ESTRUTURA = """
SELECT
    produto,
    sequencia,
    quantidade,
    componente,
    data_inclusao,
    data_alteracao
FROM ESTRUTURA
"""


def _to_datetime(series):
    """
    Converte datas, tratando '0000-00-00' e vazios como NaT.
    """
    return pd.to_datetime(
        series.replace(["0000-00-00", "0000-00-00 00:00:00", "", None], pd.NaT),
        errors="coerce"
    )


def _to_numeric(series):
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _preparar_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(
            columns=[
                "produto",
                "sequencia",
                "quantidade",
                "componente",
                "data_inclusao",
                "data_alteracao",
            ]
        )

    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]

    if "produto" in df.columns:
        df["produto"] = df["produto"].astype(str).str.strip()

    if "componente" in df.columns:
        df["componente"] = df["componente"].astype(str).str.strip()

    if "sequencia" in df.columns:
        df["sequencia"] = _to_numeric(df["sequencia"]).astype(int)

    if "quantidade" in df.columns:
        df["quantidade"] = _to_numeric(df["quantidade"])

    if "data_inclusao" in df.columns:
        df["data_inclusao"] = _to_datetime(df["data_inclusao"])

    if "data_alteracao" in df.columns:
        df["data_alteracao"] = _to_datetime(df["data_alteracao"])

    return df


def _get_periodo_mes_atual():
    hoje = pd.Timestamp.today().normalize()
    primeiro_dia_mes = hoje.replace(day=1)
    primeiro_dia_proximo_mes = primeiro_dia_mes + pd.DateOffset(months=1)
    return primeiro_dia_mes, primeiro_dia_proximo_mes


def _get_periodo_mes_anterior():
    hoje = pd.Timestamp.today().normalize()
    primeiro_dia_mes_atual = hoje.replace(day=1)
    primeiro_dia_mes_anterior = primeiro_dia_mes_atual - pd.DateOffset(months=1)
    return primeiro_dia_mes_anterior, primeiro_dia_mes_atual


def _criar_masks_periodo(df: pd.DataFrame, dt_inicio, dt_fim):
    mask_inclusao = (
        df["data_inclusao"].notna()
        & (df["data_inclusao"] >= dt_inicio)
        & (df["data_inclusao"] < dt_fim)
    )

    mask_alteracao = (
        df["data_alteracao"].notna()
        & (df["data_alteracao"] >= dt_inicio)
        & (df["data_alteracao"] < dt_fim)
    )

    return mask_inclusao, mask_alteracao


def _calcular_metricas_periodo(df: pd.DataFrame, dt_inicio, dt_fim) -> dict:
    if df.empty:
        return {
            "qtd_estruturas_incluidas": 0,
            "qtd_estruturas_alteradas": 0,
            "qtd_componentes_alterados": 0,
            "qtd_alteracoes": 0,
            "qtd_itens_principais_alterados": 0,
        }

    mask_inclusao, mask_alteracao = _criar_masks_periodo(df, dt_inicio, dt_fim)

    # Estruturas incluídas no período:
    # considera somente item principal (sequencia 0)
    estruturas_incluidas = df[
        (df["sequencia"] == 0) & mask_inclusao
    ]["produto"].nunique()

    # Estruturas alteradas:
    # qualquer produto com alguma linha alterada no período
    estruturas_alteradas = df[mask_alteracao]["produto"].nunique()

    # Componentes alterados:
    # linhas com sequencia diferente de 0 alteradas no período
    componentes_alterados = df[
        (df["sequencia"] != 0) & mask_alteracao
    ].shape[0]

    # Alterações totais:
    alteracoes_totais = df[mask_alteracao].shape[0]

    # Alteração do item principal:
    itens_principais_alterados = df[
        (df["sequencia"] == 0) & mask_alteracao
    ].shape[0]

    return {
        "qtd_estruturas_incluidas": int(estruturas_incluidas),
        "qtd_estruturas_alteradas": int(estruturas_alteradas),
        "qtd_componentes_alterados": int(componentes_alterados),
        "qtd_alteracoes": int(alteracoes_totais),
        "qtd_itens_principais_alterados": int(itens_principais_alterados),
    }


def get_estrutura_df():
    try:
        df = run_query(SQL_ESTRUTURA)
        return _preparar_df(df)
    except Exception as e:
        st.error(f"Erro ao carregar estrutura: {e}")
        return pd.DataFrame()


def get_estrutura_mes_df():
    try:
        df = get_estrutura_df()

        if df.empty:
            return df

        dt_inicio, dt_fim = _get_periodo_mes_atual()
        mask_inclusao, mask_alteracao = _criar_masks_periodo(df, dt_inicio, dt_fim)

        df_mes = df[mask_inclusao | mask_alteracao].copy()

        if df_mes.empty:
            return df_mes

        df_mes["evento_mes"] = ""
        df_mes.loc[mask_inclusao.loc[df_mes.index], "evento_mes"] = "INCLUSAO"
        df_mes.loc[mask_alteracao.loc[df_mes.index], "evento_mes"] = "ALTERACAO"
        df_mes.loc[
            mask_inclusao.loc[df_mes.index] & mask_alteracao.loc[df_mes.index],
            "evento_mes"
        ] = "INCLUSAO/ALTERACAO"

        return df_mes.sort_values(
            by=["produto", "sequencia", "data_alteracao", "data_inclusao"],
            ascending=[True, True, False, False]
        )

    except Exception as e:
        st.error(f"Erro no módulo Estrutura: {e}")
        return pd.DataFrame()


def get_resumo_produto():
    try:
        df = get_estrutura_mes_df()

        if df.empty:
            return pd.DataFrame(
                columns=[
                    "produto",
                    "estrutura_incluida_mes",
                    "estrutura_alterada_mes",
                    "componentes_alterados",
                    "alteracoes_total",
                ]
            )

        dt_inicio, dt_fim = _get_periodo_mes_atual()
        mask_inclusao, mask_alteracao = _criar_masks_periodo(df, dt_inicio, dt_fim)

        resumo = (
            df.groupby("produto", as_index=False)
            .agg(
                estrutura_incluida_mes=(
                    "sequencia",
                    lambda s: int(((df.loc[s.index, "sequencia"] == 0) & mask_inclusao.loc[s.index]).any())
                ),
                estrutura_alterada_mes=(
                    "sequencia",
                    lambda s: int(mask_alteracao.loc[s.index].any())
                ),
                componentes_alterados=(
                    "sequencia",
                    lambda s: int(((df.loc[s.index, "sequencia"] != 0) & mask_alteracao.loc[s.index]).sum())
                ),
                alteracoes_total=(
                    "sequencia",
                    lambda s: int(mask_alteracao.loc[s.index].sum())
                ),
            )
        )

        return resumo.sort_values(
            by=["estrutura_alterada_mes", "componentes_alterados", "alteracoes_total", "produto"],
            ascending=[False, False, False, True]
        )

    except Exception as e:
        st.error(f"Erro ao gerar resumo por produto: {e}")
        return pd.DataFrame()


def get_kpi():
    try:
        df = get_estrutura_df()

        if df.empty:
            return {
                "nome": "Estruturas Alteradas",
                "valor": 0.0,
                "valor_anterior": 0.0,
                "unidade": "itens",
                "cor": "card-blue",
                "extra": "Incluídas: 0 | Alteradas: 0<br>Componentes alterados: 0 | Alterações: 0",
                "qtd_estruturas_incluidas": 0,
                "qtd_estruturas_alteradas": 0,
                "qtd_componentes_alterados": 0,
                "qtd_alteracoes": 0,
            }

        dt_inicio_atual, dt_fim_atual = _get_periodo_mes_atual()
        dt_inicio_ant, dt_fim_ant = _get_periodo_mes_anterior()

        metricas_atual = _calcular_metricas_periodo(df, dt_inicio_atual, dt_fim_atual)
        metricas_anterior = _calcular_metricas_periodo(df, dt_inicio_ant, dt_fim_ant)

        valor_atual = metricas_atual["qtd_estruturas_alteradas"]
        valor_anterior = metricas_anterior["qtd_estruturas_alteradas"]

        extra = (
            f"Incluídas: {metricas_atual['qtd_estruturas_incluidas']} | "
            f"Alteradas: {metricas_atual['qtd_estruturas_alteradas']}<br>"
            f"Componentes alterados: {metricas_atual['qtd_componentes_alterados']} | "
            f"Alterações: {metricas_atual['qtd_alteracoes']}"
        )

        return {
            "nome": "Estruturas Alteradas",
            "valor": float(valor_atual),
            "valor_anterior": float(valor_anterior),
            "unidade": "itens",
            "cor": "card-blue",
            "extra": extra,
            "qtd_estruturas_incluidas": metricas_atual["qtd_estruturas_incluidas"],
            "qtd_estruturas_alteradas": metricas_atual["qtd_estruturas_alteradas"],
            "qtd_componentes_alterados": metricas_atual["qtd_componentes_alterados"],
            "qtd_alteracoes": metricas_atual["qtd_alteracoes"],
        }

    except Exception as e:
        st.error(f"Erro no módulo Estrutura: {e}")
        return {
            "nome": "Estruturas Alteradas",
            "valor": 0.0,
            "valor_anterior": 0.0,
            "unidade": "itens",
            "cor": "card-blue",
            "extra": "Incluídas: 0 | Alteradas: 0<br>Componentes alterados: 0 | Alterações: 0",
            "qtd_estruturas_incluidas": 0,
            "qtd_estruturas_alteradas": 0,
            "qtd_componentes_alterados": 0,
            "qtd_alteracoes": 0,
        }


def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])