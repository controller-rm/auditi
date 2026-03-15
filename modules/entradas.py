from pathlib import Path
import pandas as pd
from services.query_service import run_query

BASE_DIR = Path(__file__).resolve().parent.parent
ARQUIVO_CME = BASE_DIR / "data" / "CME_ADEX.csv"

SQL_COMPRAS = """
SELECT
    inf.codigo_cliente_fornecedor,
    inf.numero_documento,
    nf.serie_documento,
    inf.origem,
    inf.codigo_produto,
    inf.descricao_produto,
    p.tipo_material,
    inf.quantidade,
    inf.valor_total,
    nf.data_recepcao_documento
FROM ITENS_NOTA_FISCAL inf
INNER JOIN (
    SELECT
        codigo_cliente_fornecedor,
        numero_documento,
        serie_documento,
        MAX(data_recepcao_documento) AS data_recepcao_documento
    FROM NOTA_FISCAL
    WHERE tipo_documento = 'E'
      AND data_recepcao_documento >= DATE_FORMAT(DATE_SUB(CURDATE(), INTERVAL 2 MONTH), '%Y-%m-01')
      AND data_recepcao_documento < DATE_ADD(LAST_DAY(CURDATE()), INTERVAL 1 DAY)
    GROUP BY
        codigo_cliente_fornecedor,
        numero_documento,
        serie_documento
) nf
    ON nf.codigo_cliente_fornecedor = inf.codigo_cliente_fornecedor
   AND nf.numero_documento = inf.numero_documento
   AND nf.serie_documento = inf.serie_documento
LEFT JOIN PRODUTO p
    ON p.codigo_produto_material = inf.codigo_produto
"""


def formatar_inteiro_br(valor):
    try:
        return f"{int(valor or 0):,}".replace(",", ".")
    except Exception:
        return "0"


def formatar_moeda_br(valor):
    try:
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def normalizar_texto(coluna):
    return coluna.astype(str).str.strip().str.upper()


def carregar_cme():
    df_cme = pd.read_csv(
        ARQUIVO_CME,
        sep=";",
        dtype=str,
        encoding="latin1"
    )

    df_cme.columns = [col.strip() for col in df_cme.columns]

    if "Origem" not in df_cme.columns or "CME" not in df_cme.columns:
        raise ValueError("O arquivo CME_ADEX.csv deve conter as colunas 'Origem' e 'CME'.")

    df_cme["Origem"] = normalizar_texto(df_cme["Origem"])
    df_cme["CME"] = df_cme["CME"].astype(str).str.strip()

    df_cme = (
        df_cme[["Origem", "CME"]]
        .dropna(subset=["Origem"])
        .drop_duplicates(subset=["Origem"], keep="first")
    )

    return df_cme


def preparar_base_compras():
    df = run_query(SQL_COMPRAS)

    if df is None or df.empty:
        return pd.DataFrame()

    df.columns = [col.strip() for col in df.columns]

    df["codigo_cliente_fornecedor"] = df["codigo_cliente_fornecedor"].astype(str).str.strip()
    df["numero_documento"] = df["numero_documento"].astype(str).str.strip()
    df["serie_documento"] = normalizar_texto(df["serie_documento"])
    df["origem"] = normalizar_texto(df["origem"])
    df["codigo_produto"] = df["codigo_produto"].astype(str).str.strip()

    df["tipo_material"] = (
        df["tipo_material"]
        .fillna("SEM TIPO")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["quantidade"] = pd.to_numeric(df["quantidade"], errors="coerce").fillna(0)
    df["valor_total"] = pd.to_numeric(df["valor_total"], errors="coerce").fillna(0)

    df["data_recepcao_documento"] = pd.to_datetime(
        df["data_recepcao_documento"], errors="coerce"
    )

    df = df.dropna(subset=["data_recepcao_documento"]).copy()

    # valor_total já representa o total do item
    df["valor_total_item"] = df["valor_total"]

    df_cme = carregar_cme()

    df = df.merge(
        df_cme,
        left_on="origem",
        right_on="Origem",
        how="left"
    )

    df = df[df["CME"] == "110"].copy()

    return df


def get_entradas_mes_df():
    df = preparar_base_compras()

    if df.empty:
        return pd.DataFrame()

    hoje = pd.Timestamp.today().normalize()
    primeiro_dia_mes = hoje.replace(day=1)
    primeiro_dia_proximo_mes = primeiro_dia_mes + pd.DateOffset(months=1)

    df_mes = df[
        (df["data_recepcao_documento"] >= primeiro_dia_mes) &
        (df["data_recepcao_documento"] < primeiro_dia_proximo_mes)
    ].copy()

    colunas_ordem = [
        "data_recepcao_documento",
        "codigo_cliente_fornecedor",
        "numero_documento",
        "serie_documento",
        "origem",
        "CME",
        "codigo_produto",
        "descricao_produto",
        "tipo_material",
        "quantidade",
        "valor_total",
        "valor_total_item",
    ]

    colunas_existentes = [c for c in colunas_ordem if c in df_mes.columns]
    if colunas_existentes:
        df_mes = df_mes[colunas_existentes]

    return df_mes


def get_entradas_por_tipo_material():
    df_mes = get_entradas_mes_df()

    if df_mes.empty:
        return pd.DataFrame(
            columns=["tipo_material", "quantidade_total", "valor_total_entrada"]
        )

    resumo = (
        df_mes.groupby("tipo_material", as_index=False)
        .agg(
            quantidade_total=("quantidade", "sum"),
            valor_total_entrada=("valor_total_item", "sum")
        )
        .sort_values("valor_total_entrada", ascending=False)
    )

    return resumo


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


def get_kpi():
    try:
        df = preparar_base_compras()

        if df.empty:
            return {
                "nome": "Compras Mês",
                "valor": 0.0,
                "valor_anterior": 0.0,
                "unidade": "R$",
                "cor": "card-pink",
                "extra": "0 notas fiscais lançadas no mês"
            }

        hoje = pd.Timestamp.today().normalize()
        primeiro_dia_mes = hoje.replace(day=1)
        primeiro_dia_proximo_mes = primeiro_dia_mes + pd.DateOffset(months=1)
        primeiro_dia_mes_anterior = primeiro_dia_mes - pd.DateOffset(months=1)

        df_mes_atual = df[
            (df["data_recepcao_documento"] >= primeiro_dia_mes) &
            (df["data_recepcao_documento"] < primeiro_dia_proximo_mes)
        ].copy()

        df_mes_anterior = df[
            (df["data_recepcao_documento"] >= primeiro_dia_mes_anterior) &
            (df["data_recepcao_documento"] < primeiro_dia_mes)
        ].copy()

        valor_compras_mes = float(df_mes_atual["valor_total_item"].sum())
        valor_compras_mes_anterior = float(df_mes_anterior["valor_total_item"].sum())

        qtd_notas_mes = (
            df_mes_atual[["codigo_cliente_fornecedor", "numero_documento", "serie_documento"]]
            .drop_duplicates()
            .shape[0]
        )

        resumo_tipo = get_entradas_por_tipo_material()

        detalhes_tipo = ""
        if not resumo_tipo.empty:
            linhas = []
            for _, row in resumo_tipo.head(5).iterrows():
                linhas.append(
                    f"{row['tipo_material']}: {formatar_moeda_br(row['valor_total_entrada'])}"
                )
            detalhes_tipo = "<br>".join(linhas)

        extra = f"{formatar_inteiro_br(qtd_notas_mes)} notas fiscais lançadas no mês"
        if detalhes_tipo:
            extra += "<br>" + detalhes_tipo

        return {
            "nome": "Compras Mês",
            "valor": valor_compras_mes,
            "valor_anterior": valor_compras_mes_anterior,
            "unidade": "R$",
            "cor": "card-pink",
            "extra": extra
        }

    except Exception as e:
        return {
            "nome": "Compras Mês",
            "valor": 0.0,
            "valor_anterior": 0.0,
            "unidade": "R$",
            "cor": "card-pink",
            "extra": f"Erro ao carregar: {e}"
        }