import pandas as pd
import streamlit as st
from services.query_service import run_query


MESES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}


def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual_br(valor):
    return f"{valor:,.2f}%".replace(",", "X").replace(".", ",").replace("X", ".")


# Última competência válida da tabela de metas
SQL_REFERENCIA = """
SELECT
    ANO,
    MES
FROM METAS_VENDAS
WHERE COALESCE(COTA_VALOR, 0) > 0
ORDER BY ANO DESC, MES DESC
LIMIT 1
"""

# Card principal - mesma competência válida
SQL_KPI_META = """
SELECT
    m.ANO,
    m.MES,
    m.COD_UNICO_EMP,
    COALESCE(SUM(m.COTA_VALOR), 0) AS meta_mes,
    COALESCE(SUM(m.VALOR_FAT), 0) AS realizado_mes
FROM METAS_VENDAS m
INNER JOIN (
    SELECT
        ANO,
        MES
    FROM METAS_VENDAS
    WHERE COALESCE(COTA_VALOR, 0) > 0
    ORDER BY ANO DESC, MES DESC
    LIMIT 1
) ref
    ON m.ANO = ref.ANO
   AND m.MES = ref.MES
GROUP BY m.ANO, m.MES, m.COD_UNICO_EMP
ORDER BY m.COD_UNICO_EMP
"""

# Resumo mensal do ano da última competência válida
SQL_RESUMO_MENSAL = """
SELECT
    m.ANO,
    m.MES,
    m.COD_UNICO_EMP,
    COALESCE(SUM(m.COTA_VALOR), 0) AS meta_valor,
    COALESCE(SUM(m.VALOR_FAT), 0) AS valor_fat
FROM METAS_VENDAS m
INNER JOIN (
    SELECT
        ANO
    FROM METAS_VENDAS
    WHERE COALESCE(COTA_VALOR, 0) > 0
    ORDER BY ANO DESC, MES DESC
    LIMIT 1
) ref
    ON m.ANO = ref.ANO
GROUP BY m.ANO, m.MES, m.COD_UNICO_EMP
HAVING COALESCE(SUM(m.COTA_VALOR), 0) > 0
    OR COALESCE(SUM(m.VALOR_FAT), 0) > 0
ORDER BY m.MES, m.COD_UNICO_EMP
"""

# Tabela por representante do mesmo ano de referência
SQL_TABELA_REPRESENTANTE = """
SELECT
    m.ANO,
    m.MES,
    m.COD_UNICO_EMP,
    m.REPRESENTANTE,
    COALESCE(SUM(m.COTA_VALOR), 0) AS meta_valor,
    COALESCE(SUM(m.VALOR_FAT), 0) AS valor_fat,
    CASE
        WHEN COALESCE(SUM(m.COTA_VALOR), 0) > 0
        THEN (SUM(m.VALOR_FAT) / SUM(m.COTA_VALOR)) * 100
        ELSE 0
    END AS perc_at_fat
FROM METAS_VENDAS m
INNER JOIN (
    SELECT
        ANO
    FROM METAS_VENDAS
    WHERE COALESCE(COTA_VALOR, 0) > 0
    ORDER BY ANO DESC, MES DESC
    LIMIT 1
) ref
    ON m.ANO = ref.ANO
GROUP BY m.ANO, m.MES, m.COD_UNICO_EMP, m.REPRESENTANTE
HAVING COALESCE(SUM(m.COTA_VALOR), 0) > 0
    OR COALESCE(SUM(m.VALOR_FAT), 0) > 0
ORDER BY m.MES, m.COD_UNICO_EMP, m.REPRESENTANTE
"""


def get_referencia():
    try:
        df = run_query(SQL_REFERENCIA)

        if df is None or df.empty:
            return None, None

        ano_ref = int(df.iloc[0]["ANO"]) if pd.notna(df.iloc[0]["ANO"]) else None
        mes_ref = int(df.iloc[0]["MES"]) if pd.notna(df.iloc[0]["MES"]) else None

        return ano_ref, mes_ref

    except Exception as e:
        st.error(f"Erro ao obter referência da meta: {e}")
        return None, None


def get_kpi():
    try:
        df = run_query(SQL_KPI_META)
        ano_ref, mes_ref = get_referencia()

        if df is None or df.empty:
            return {
                "nome": "% Faltante p/ Meta",
                "valor": 0,
                "valor_anterior": 0,
                "unidade": "%",
                "cor": "card-orange",
                "extra": "Sem dados de meta.",
                "extra_obs": "Incluir informações sobre os valores do card."
            }

        df["meta_mes"] = pd.to_numeric(df["meta_mes"], errors="coerce").fillna(0.0)
        df["realizado_mes"] = pd.to_numeric(df["realizado_mes"], errors="coerce").fillna(0.0)

        meta_mes = float(df["meta_mes"].sum())
        realizado_mes = float(df["realizado_mes"].sum())

        perc_atingido = (realizado_mes / meta_mes * 100) if meta_mes > 0 else 0
        perc_faltante = max(0, 100 - perc_atingido)
        faltante_valor = max(0, meta_mes - realizado_mes)

        mes_nome = MESES.get(mes_ref, str(mes_ref)) if mes_ref else "-"
        referencia_txt = f"{mes_nome}/{ano_ref}" if ano_ref else "-"

        filiais = []
        for _, row in df.iterrows():
            filial = row["COD_UNICO_EMP"]
            realizado_filial = float(row["realizado_mes"] or 0)
            filiais.append(f"{filial}: {formatar_moeda_br(realizado_filial)}")

        extra = (
            f"Referência: {referencia_txt}<br>"
            f"Meta mês: {formatar_moeda_br(meta_mes)}<br>"
            f"Realizado: {formatar_moeda_br(realizado_mes)}<br>"
            f"Faltante: {formatar_moeda_br(faltante_valor)}"
        )

        if filiais:
            extra += "<br><br>" + "<br>".join(filiais)

        return {
            "nome": "% Faltante p/ Meta",
            "valor": perc_faltante,
            "valor_anterior": perc_atingido,
            "unidade": "%",
            "cor": "card-orange" if perc_faltante > 0 else "card-green",
            "extra": extra,
            "extra_obs": "Incluir informações sobre os valores do card.",
            "meta_mes": meta_mes,
            "realizado_mes": realizado_mes,
            "faltante_valor": faltante_valor,
            "perc_atingido": perc_atingido,
            "perc_faltante": perc_faltante,
        }

    except Exception as e:
        st.error(f"Erro no módulo Meta Atingida: {e}")
        return {
            "nome": "% Faltante p/ Meta",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "%",
            "cor": "card-orange",
            "extra": None,
            "extra_obs": "Incluir informações sobre os valores do card."
        }


def get_resumo_mensal():
    try:
        df = run_query(SQL_RESUMO_MENSAL)

        if df is None or df.empty:
            return pd.DataFrame(
                columns=[
                    "Mês",
                    "Filial",
                    "Meta",
                    "Realizado",
                    "% Atingido",
                    "% Faltante",
                    "Faltante Valor",
                ]
            )

        df["MES"] = pd.to_numeric(df["MES"], errors="coerce").fillna(0).astype(int)
        df["meta_valor"] = pd.to_numeric(df["meta_valor"], errors="coerce").fillna(0.0)
        df["valor_fat"] = pd.to_numeric(df["valor_fat"], errors="coerce").fillna(0.0)

        df["% Atingido"] = df.apply(
            lambda row: (row["valor_fat"] / row["meta_valor"] * 100)
            if row["meta_valor"] > 0 else 0,
            axis=1
        )
        df["% Faltante"] = df["% Atingido"].apply(lambda x: max(0, 100 - x))
        df["Faltante Valor"] = (df["meta_valor"] - df["valor_fat"]).apply(lambda x: max(0, x))
        df["Mês"] = df["MES"].map(MESES)
        df["Filial"] = df["COD_UNICO_EMP"]

        return df.rename(columns={
            "meta_valor": "Meta",
            "valor_fat": "Realizado",
        })[
            ["Mês", "Filial", "Meta", "Realizado", "% Atingido", "% Faltante", "Faltante Valor"]
        ]

    except Exception as e:
        st.error(f"Erro ao buscar resumo mensal das metas: {e}")
        return pd.DataFrame(
            columns=[
                "Mês",
                "Filial",
                "Meta",
                "Realizado",
                "% Atingido",
                "% Faltante",
                "Faltante Valor",
            ]
        )


def get_tabela_anual():
    try:
        df = run_query(SQL_TABELA_REPRESENTANTE)

        if df is None or df.empty:
            return pd.DataFrame()

        df["MES"] = pd.to_numeric(df["MES"], errors="coerce").fillna(0).astype(int)
        df["meta_valor"] = pd.to_numeric(df["meta_valor"], errors="coerce").fillna(0.0)
        df["valor_fat"] = pd.to_numeric(df["valor_fat"], errors="coerce").fillna(0.0)
        df["perc_at_fat"] = pd.to_numeric(df["perc_at_fat"], errors="coerce").fillna(0.0)

        df["CHAVE"] = (
            df["REPRESENTANTE"].fillna("SEM REPRESENTANTE")
            + " - "
            + df["COD_UNICO_EMP"].fillna("SEM FILIAL")
        )

        base = pd.DataFrame({"REPRESENTANTE": sorted(df["CHAVE"].unique())})

        meses_existentes = sorted(df["MES"].unique().tolist())
        tabela = base.copy()

        for mes_num in meses_existentes:
            mes_nome = MESES.get(mes_num, f"Mês_{mes_num}")
            df_mes = df[df["MES"] == mes_num].copy()

            meta_map = df_mes.groupby("CHAVE")["meta_valor"].sum()
            real_map = df_mes.groupby("CHAVE")["valor_fat"].sum()
            perc_map = df_mes.groupby("CHAVE")["perc_at_fat"].mean()

            tabela[f"{mes_nome}_Meta"] = tabela["REPRESENTANTE"].map(meta_map).fillna(0.0)
            tabela[f"{mes_nome}_Realizado"] = tabela["REPRESENTANTE"].map(real_map).fillna(0.0)
            tabela[f"{mes_nome}_%"] = tabela["REPRESENTANTE"].map(perc_map).fillna(0.0)

        return tabela

    except Exception as e:
        st.error(f"Erro ao montar tabela anual de metas: {e}")
        return pd.DataFrame()


def formatar_tabela_anual(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df_fmt = df.copy()

    for col in df_fmt.columns:
        if col == "REPRESENTANTE":
            continue
        elif col.endswith("_%"):
            df_fmt[col] = df_fmt[col].apply(formatar_percentual_br)
        else:
            df_fmt[col] = df_fmt[col].apply(formatar_moeda_br)

    return df_fmt




def get_tabela_meta_matriz():
    try:
        df = run_query(SQL_TABELA_REPRESENTANTE)

        if df is None or df.empty:
            return pd.DataFrame()

        df["MES"] = pd.to_numeric(df["MES"], errors="coerce").fillna(0).astype(int)
        df["meta_valor"] = pd.to_numeric(df["meta_valor"], errors="coerce").fillna(0.0)
        df["valor_fat"] = pd.to_numeric(df["valor_fat"], errors="coerce").fillna(0.0)
        df["perc_at_fat"] = pd.to_numeric(df["perc_at_fat"], errors="coerce").fillna(0.0)

        df["REPRESENTANTE"] = df["REPRESENTANTE"].fillna("SEM REPRESENTANTE")
        df["COD_UNICO_EMP"] = df["COD_UNICO_EMP"].fillna("SEM FILIAL")
        df["CHAVE"] = df["REPRESENTANTE"] + " - " + df["COD_UNICO_EMP"]

        meses_existentes = sorted(df["MES"].unique().tolist())

        base = pd.DataFrame({"REPRESENTANTE": sorted(df["CHAVE"].unique())})

        for mes_num in meses_existentes:
            mes_nome = MESES.get(mes_num, f"Mês_{mes_num}")
            df_mes = df[df["MES"] == mes_num].copy()

            meta_map = df_mes.groupby("CHAVE")["meta_valor"].sum()
            real_map = df_mes.groupby("CHAVE")["valor_fat"].sum()
            perc_map = df_mes.groupby("CHAVE")["perc_at_fat"].mean()

            base[(mes_nome, "Meta 2026")] = base["REPRESENTANTE"].map(meta_map).fillna(0.0)
            base[(mes_nome, "Realizado")] = base["REPRESENTANTE"].map(real_map).fillna(0.0)
            base[(mes_nome, "%")] = base["REPRESENTANTE"].map(perc_map).fillna(0.0)

        # transforma a primeira coluna em multiindex também
        colunas = []
        for col in base.columns:
            if isinstance(col, tuple):
                colunas.append(col)
            else:
                colunas.append((" ", col))

        base.columns = pd.MultiIndex.from_tuples(colunas)

        # linha total
        total = {}
        total[(" ", "REPRESENTANTE")] = "TOTAL"

        for mes_num in meses_existentes:
            mes_nome = MESES.get(mes_num, f"Mês_{mes_num}")

            col_meta = (mes_nome, "Meta 2026")
            col_real = (mes_nome, "Realizado")
            col_perc = (mes_nome, "%")

            soma_meta = base[col_meta].sum()
            soma_real = base[col_real].sum()
            perc_total = (soma_real / soma_meta * 100) if soma_meta > 0 else 0

            total[col_meta] = soma_meta
            total[col_real] = soma_real
            total[col_perc] = perc_total

        base = pd.concat([base, pd.DataFrame([total])], ignore_index=True)

        return base

    except Exception as e:
        st.error(f"Erro ao montar matriz de metas: {e}")
        return pd.DataFrame()

def formatar_tabela_meta_matriz(df):
    if df is None or df.empty:
        return pd.DataFrame()

    df_fmt = df.copy()

    for col in df_fmt.columns:
        if col == (" ", "REPRESENTANTE"):
            continue

        if isinstance(col, tuple) and len(col) == 2:
            if col[1] == "%":
                df_fmt[col] = df_fmt[col].apply(formatar_percentual_br)
            else:
                df_fmt[col] = df_fmt[col].apply(formatar_moeda_br)

    return df_fmt
