import pandas as pd
import streamlit as st
from services.query_service import run_query


SQL_PROD_PARADA_KPI = """
WITH ordem_base AS (
    SELECT DISTINCT
        TRIM(ofa.nro_of) AS nro_of,
        SUBSTRING_INDEX(TRIM(ofa.produto), ' ', 1) AS cod_produto,
        CONCAT(
            TRIM(ofa.nro_of), '|',
            SUBSTRING_INDEX(TRIM(ofa.produto), ' ', 1)
        ) AS chave_of
    FROM ORDEM_FABRIC ofa
    WHERE TRIM(ofa.nro_of) <> ''
      AND TRIM(COALESCE(ofa.status_of, '')) = 'A'
      AND COALESCE(ofa.origem, 0) NOT IN (997, 999)
),
horas_base AS (
    SELECT
        TRIM(ht.nro_of) AS nro_of,
        SUBSTRING_INDEX(TRIM(ht.produto), ' ', 1) AS cod_produto,
        CONCAT(
            TRIM(ht.nro_of), '|',
            SUBSTRING_INDEX(TRIM(ht.produto), ' ', 1)
        ) AS chave_of,
        COALESCE(ht.seq_ap_of, 0) AS seq_ap_of,
        DATE(ht.data_abertura) AS data_abertura,
        DATE(ht.data_fechamento) AS data_fechamento,
        TRIM(ht.equipamento) AS equipamento,
        TRIM(ht.desc_equipamento) AS desc_equipamento,
        TRIM(ht.cod_operador) AS cod_operador,
        TRIM(ht.desc_operador) AS desc_operador,
        ht.horas_of
    FROM HORAS_TRAB ht
    WHERE TRIM(ht.nro_of) <> ''
),
base_filtrada AS (
    SELECT hb.*
    FROM horas_base hb
    INNER JOIN ordem_base ob
        ON hb.chave_of = ob.chave_of
),
ultima_seq AS (
    SELECT
        chave_of,
        MAX(seq_ap_of) AS max_seq_ap_of
    FROM base_filtrada
    GROUP BY chave_of
),
paradas_base AS (
    SELECT
        bf.nro_of,
        bf.cod_produto,
        bf.chave_of,
        bf.seq_ap_of,
        bf.data_abertura,
        bf.data_fechamento,
        CASE
            WHEN bf.data_fechamento IS NULL
                THEN DATEDIFF(CURDATE(), bf.data_abertura)
            ELSE DATEDIFF(CURDATE(), bf.data_fechamento)
        END AS dias_parada
    FROM base_filtrada bf
    INNER JOIN ultima_seq us
        ON bf.chave_of = us.chave_of
       AND bf.seq_ap_of = us.max_seq_ap_of
)
SELECT
    SUM(CASE WHEN dias_parada > 5 THEN 1 ELSE 0 END) AS qtd_total_paradas,
    SUM(CASE WHEN dias_parada > 5 THEN 1 ELSE 0 END) AS qtd_mais_5,
    SUM(CASE WHEN dias_parada > 10 THEN 1 ELSE 0 END) AS qtd_mais_10,
    SUM(CASE WHEN dias_parada > 15 THEN 1 ELSE 0 END) AS qtd_mais_15
FROM paradas_base;
"""


SQL_PROD_PARADA_DETALHE = """
WITH ordem_base AS (
    SELECT DISTINCT
        TRIM(ofa.nro_of) AS nro_of,
        TRIM(ofa.produto) AS produto_ordem,
        SUBSTRING_INDEX(TRIM(ofa.produto), ' ', 1) AS cod_produto,
        CONCAT(
            TRIM(ofa.nro_of), '|',
            SUBSTRING_INDEX(TRIM(ofa.produto), ' ', 1)
        ) AS chave_of
    FROM ORDEM_FABRIC ofa
    WHERE TRIM(ofa.nro_of) <> ''
      AND TRIM(COALESCE(ofa.status_of, '')) = 'A'
      AND COALESCE(ofa.origem, 0) NOT IN (997, 999)
),
horas_base AS (
    SELECT
        TRIM(ht.nro_of) AS nro_of,
        TRIM(ht.produto) AS produto_hora,
        SUBSTRING_INDEX(TRIM(ht.produto), ' ', 1) AS cod_produto,
        CONCAT(
            TRIM(ht.nro_of), '|',
            SUBSTRING_INDEX(TRIM(ht.produto), ' ', 1)
        ) AS chave_of,
        COALESCE(ht.seq_ap_of, 0) AS seq_ap_of,
        DATE(ht.data_abertura) AS data_abertura,
        DATE(ht.data_fechamento) AS data_fechamento,
        TRIM(ht.equipamento) AS equipamento,
        TRIM(ht.desc_equipamento) AS desc_equipamento,
        TRIM(ht.cod_operador) AS cod_operador,
        TRIM(ht.desc_operador) AS desc_operador,
        ht.horas_of
    FROM HORAS_TRAB ht
    WHERE TRIM(ht.nro_of) <> ''
),
base_filtrada AS (
    SELECT
        hb.nro_of,
        hb.cod_produto,
        hb.produto_hora,
        ob.produto_ordem,
        hb.chave_of,
        hb.seq_ap_of,
        hb.data_abertura,
        hb.data_fechamento,
        hb.equipamento,
        hb.desc_equipamento,
        hb.cod_operador,
        hb.desc_operador,
        hb.horas_of
    FROM horas_base hb
    INNER JOIN ordem_base ob
        ON hb.chave_of = ob.chave_of
),
ultima_seq AS (
    SELECT
        chave_of,
        MAX(seq_ap_of) AS max_seq_ap_of
    FROM base_filtrada
    GROUP BY chave_of
),
paradas_base AS (
    SELECT
        bf.nro_of,
        bf.cod_produto,
        bf.produto_hora,
        bf.produto_ordem,
        bf.chave_of,
        bf.seq_ap_of,
        bf.data_abertura,
        bf.data_fechamento,
        bf.equipamento,
        bf.desc_equipamento,
        bf.cod_operador,
        bf.desc_operador,
        bf.horas_of,
        CASE
            WHEN bf.data_fechamento IS NULL
                THEN DATEDIFF(CURDATE(), bf.data_abertura)
            ELSE DATEDIFF(CURDATE(), bf.data_fechamento)
        END AS dias_parada
    FROM base_filtrada bf
    INNER JOIN ultima_seq us
        ON bf.chave_of = us.chave_of
       AND bf.seq_ap_of = us.max_seq_ap_of
)
SELECT
    nro_of,
    cod_produto,
    produto_ordem,
    produto_hora,
    chave_of,
    seq_ap_of,
    data_abertura,
    data_fechamento,
    equipamento,
    desc_equipamento,
    cod_operador,
    desc_operador,
    horas_of,
    dias_parada,
    CASE
        WHEN dias_parada > 15 THEN '15+ dias'
        WHEN dias_parada > 10 THEN '11 a 15 dias'
        WHEN dias_parada > 5 THEN '6 a 10 dias'
    END AS faixa_parada
FROM paradas_base
WHERE dias_parada > 5
ORDER BY dias_parada DESC, nro_of;
)
SELECT
    nro_of,
    cod_produto,
    produto_ordem,
    produto_hora,
    chave_of,
    seq_ap_of,
    data_abertura,
    data_fechamento,
    equipamento,
    desc_equipamento,
    cod_operador,
    desc_operador,
    horas_of,
    dias_parada,
    CASE
        WHEN dias_parada > 15 THEN '15+ dias'
        WHEN dias_parada > 10 THEN '11 a 15 dias'
        WHEN dias_parada > 5 THEN '6 a 10 dias'
    END AS faixa_parada
FROM paradas_base
WHERE dias_parada > 5
ORDER BY dias_parada DESC, nro_of;
"""


def formatar_numero_br(valor, casas=0):
    try:
        return f"{float(valor):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "0"


@st.cache_data(ttl=300)
def get_kpi():
    try:
        df = run_query(SQL_PROD_PARADA_KPI)

        if df.empty:
            return {
                "nome": "OFs Paradas",
                "valor": 0,
                "valor_anterior": 0,
                "unidade": "",
                "cor": "card-pink",
                "extra": "Sem dados para o período",
                "qtd_total_paradas": 0,
                "qtd_mais_5": 0,
                "qtd_mais_10": 0,
                "qtd_mais_15": 0,
            }

        row = df.iloc[0].fillna(0)

        qtd_mais_5 = int(row.get("qtd_mais_5", 0) or 0)
        qtd_mais_10 = int(row.get("qtd_mais_10", 0) or 0)
        qtd_mais_15 = int(row.get("qtd_mais_15", 0) or 0)

        qtd_total_paradas = qtd_mais_5 + qtd_mais_10 + qtd_mais_15

        return {
            "nome": "OFs Paradas",
            "valor": qtd_total_paradas,
            "valor_anterior": qtd_mais_10,
            "unidade": "",
            "cor": "card-pink",
            "extra": (
                f"> 5 dias: {qtd_mais_5}<br>"
                f"> 10 dias: {qtd_mais_10}<br>"
                f"> 15 dias: {qtd_mais_15}"
            ),
            "qtd_total_paradas": qtd_total_paradas,
            "qtd_mais_5": qtd_mais_5,
            "qtd_mais_10": qtd_mais_10,
            "qtd_mais_15": qtd_mais_15,
            "extra_obs": "Desconsiderando Ofs 997 e 999"
        }

    except Exception as e:
        return {
            "nome": "OFs Paradas",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "",
            "cor": "card-pink",
            "extra": f"Erro ao carregar: {str(e)}",
            "qtd_total_paradas": 0,
            "qtd_mais_5": 0,
            "qtd_mais_10": 0,
            "qtd_mais_15": 0,
        }


@st.cache_data(ttl=300)
def get_detalhe():
    try:
        df = run_query(SQL_PROD_PARADA_DETALHE)
        if df.empty:
            return pd.DataFrame(columns=[
                "nro_of", "cod_produto", "produto_ordem", "produto_hora", "chave_of",
                "seq_ap_of", "data_abertura", "data_fechamento", "equipamento",
                "desc_equipamento", "cod_operador", "desc_operador", "horas_of",
                "dias_parada", "faixa_parada"
            ])
        return df
    except Exception:
        return pd.DataFrame(columns=[
            "nro_of", "cod_produto", "produto_ordem", "produto_hora", "chave_of",
            "seq_ap_of", "data_abertura", "data_fechamento", "equipamento",
            "desc_equipamento", "cod_operador", "desc_operador", "horas_of",
            "dias_parada", "faixa_parada"
        ])


def preparar_csv_brasileiro(df):
    df_export = df.copy()

    for col in df_export.columns:
        if pd.api.types.is_datetime64_any_dtype(df_export[col]):
            df_export[col] = df_export[col].dt.strftime("%d/%m/%Y")

    return df_export.to_csv(index=False, sep=";", encoding="utf-8-sig")


def main():
    st.subheader("Produção Parada")

    kpi = get_kpi()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total paradas", formatar_numero_br(kpi["qtd_total_paradas"]))
    c2.metric("> 5 dias", formatar_numero_br(kpi["qtd_mais_5"]))
    c3.metric("> 10 dias", formatar_numero_br(kpi["qtd_mais_10"]))
    c4.metric("> 15 dias", formatar_numero_br(kpi["qtd_mais_15"]))

    df = get_detalhe()

    st.markdown("### Detalhamento das OFs paradas")

    if df.empty:
        st.info("Nenhuma OF parada encontrada.")
        return

    df_exibir = df.copy()

    if "data_abertura" in df_exibir.columns:
        df_exibir["data_abertura"] = pd.to_datetime(df_exibir["data_abertura"], errors="coerce")
        df_exibir["data_abertura"] = df_exibir["data_abertura"].dt.strftime("%d/%m/%Y")

    if "data_fechamento" in df_exibir.columns:
        df_exibir["data_fechamento"] = pd.to_datetime(df_exibir["data_fechamento"], errors="coerce")
        df_exibir["data_fechamento"] = df_exibir["data_fechamento"].dt.strftime("%d/%m/%Y")

    st.dataframe(df_exibir, use_container_width=True, hide_index=True)

    csv = preparar_csv_brasileiro(df)
    st.download_button(
        label="Baixar CSV para validação",
        data=csv,
        file_name="prod_parada_validacao.csv",
        mime="text/csv",
    )
