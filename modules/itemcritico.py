import pandas as pd
from services.query_service import run_query

SQL_ITEM_CRITICO = """
SELECT
    p.codigo_produto_material,
    p.estoque_minimo,
    p.unidade_medida,
    p.peso_especifico,
    p.estoque_fisico,
    p.pedidos_em_aberto,
    pea.produto,
    pea.tipo_material,
    pea.descricao_grupo,
    pea.quantidade,
    pea.custo_unitario,
    pea.pend_em_planej,
    pea.pen_em_sol_comp,
    pea.pend_em_ord_comp,
    pea.pend_em_producao
FROM PRODUTO p
LEFT JOIN POSICAO_ESTOQUE_ATUAL pea
    ON p.codigo_produto_material = pea.produto
"""

TIPOS_MATERIAIS_VALIDOS = ["PA", "FO", "MP", "PI"]


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


def carregar_dados():
    df = run_query(SQL_ITEM_CRITICO)

    if df is None or df.empty:
        return pd.DataFrame()

    colunas_numericas = [
        "estoque_minimo",
        "peso_especifico",
        "estoque_fisico",
        "pedidos_em_aberto",
        "quantidade",
        "custo_unitario",
        "pend_em_planej",
        "pen_em_sol_comp",
        "pend_em_ord_comp",
        "pend_em_producao",
    ]

    for col in colunas_numericas:
        if col in df.columns:
            df[col] = df[col].apply(_to_float)

    if "tipo_material" in df.columns:
        df["tipo_material"] = (
            df["tipo_material"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

    if "descricao_grupo" in df.columns:
        df["descricao_grupo"] = (
            df["descricao_grupo"]
            .fillna("SEM GRUPO")
            .astype(str)
            .str.strip()
        )

    return df


def classificar_item(row):
    estoque_minimo = row.get("estoque_minimo", 0.0)
    estoque_fisico = row.get("estoque_fisico", 0.0)

    pend_em_planej = row.get("pend_em_planej", 0.0)
    pen_em_sol_comp = row.get("pen_em_sol_comp", 0.0)
    pend_em_ord_comp = row.get("pend_em_ord_comp", 0.0)

    if estoque_fisico >= estoque_minimo:
        return "OK"

    soma_pendencias = pend_em_planej + pen_em_sol_comp + pend_em_ord_comp

    if soma_pendencias > 0 and (estoque_fisico + soma_pendencias) >= estoque_minimo:
        return "OK"

    return "CRITICO"


def get_dataframe_itens_criticos():
    df = carregar_dados()

    if df.empty:
        return pd.DataFrame()

    df["classificacao"] = df.apply(classificar_item, axis=1)

    df["faltante_minimo"] = (
        df["estoque_minimo"]
        - (
            df["estoque_fisico"]
            + df["pend_em_planej"]
            + df["pen_em_sol_comp"]
            + df["pend_em_ord_comp"]
        )
    ).clip(lower=0)

    df["custo_critico_total"] = df["faltante_minimo"] * df["custo_unitario"]

    df_criticos = df[df["classificacao"] == "CRITICO"].copy()

    colunas_saida = [
        "codigo_produto_material",
        "produto",
        "tipo_material",
        "descricao_grupo",
        "unidade_medida",
        "estoque_minimo",
        "estoque_fisico",
        "pend_em_planej",
        "pen_em_sol_comp",
        "pend_em_ord_comp",
        "pend_em_producao",
        "pedidos_em_aberto",
        "quantidade",
        "custo_unitario",
        "faltante_minimo",
        "custo_critico_total",
        "classificacao",
    ]

    colunas_existentes = [col for col in colunas_saida if col in df_criticos.columns]

    return df_criticos[colunas_existentes].sort_values(
        by=["tipo_material", "descricao_grupo", "faltante_minimo", "codigo_produto_material"],
        ascending=[True, True, False, True]
    )


def get_resumo_por_tipo_material():
    df_criticos = get_dataframe_itens_criticos()

    if df_criticos.empty:
        return pd.DataFrame({
            "tipo_material": TIPOS_MATERIAIS_VALIDOS,
            "descricao_grupo": [""] * len(TIPOS_MATERIAIS_VALIDOS),
            "qtd_itens_criticos": [0] * len(TIPOS_MATERIAIS_VALIDOS),
            "faltante_total": [0.0] * len(TIPOS_MATERIAIS_VALIDOS),
            "custo_total_critico": [0.0] * len(TIPOS_MATERIAIS_VALIDOS),
        })

    resumo = (
        df_criticos[df_criticos["tipo_material"].isin(TIPOS_MATERIAIS_VALIDOS)]
        .groupby(["tipo_material", "descricao_grupo"], as_index=False)
        .agg(
            qtd_itens_criticos=("codigo_produto_material", "count"),
            faltante_total=("faltante_minimo", "sum"),
            custo_total_critico=("custo_critico_total", "sum"),
        )
        .sort_values(
            by=["tipo_material", "custo_total_critico", "qtd_itens_criticos"],
            ascending=[True, False, False]
        )
    )

    return resumo


def get_resumo_somente_tipo_material():
    df_criticos = get_dataframe_itens_criticos()

    if df_criticos.empty:
        return pd.DataFrame({
            "tipo_material": TIPOS_MATERIAIS_VALIDOS,
            "qtd_itens_criticos": [0, 0, 0, 0],
            "faltante_total": [0.0, 0.0, 0.0, 0.0],
            "custo_total_critico": [0.0, 0.0, 0.0, 0.0],
        })

    resumo = (
        df_criticos[df_criticos["tipo_material"].isin(TIPOS_MATERIAIS_VALIDOS)]
        .groupby("tipo_material", as_index=False)
        .agg(
            qtd_itens_criticos=("codigo_produto_material", "count"),
            faltante_total=("faltante_minimo", "sum"),
            custo_total_critico=("custo_critico_total", "sum"),
        )
    )

    base = pd.DataFrame({"tipo_material": TIPOS_MATERIAIS_VALIDOS})
    resumo = base.merge(resumo, on="tipo_material", how="left").fillna(0)

    resumo["qtd_itens_criticos"] = resumo["qtd_itens_criticos"].astype(int)

    return resumo


def get_kpi():
    df_criticos = get_dataframe_itens_criticos()
    resumo_tipo_grupo = get_resumo_por_tipo_material()

    total_criticos = len(df_criticos)
    custo_total_geral = float(df_criticos["custo_critico_total"].sum()) if not df_criticos.empty else 0.0

    if resumo_tipo_grupo.empty:
        detalhes = "Sem itens críticos"
    else:
        top_grupos = resumo_tipo_grupo.sort_values(
            by="custo_total_critico",
            ascending=False
        ).head(5) # Top 10 

        detalhes_linhas = []

        for _, row in top_grupos.iterrows():
            detalhes_linhas.append(
                f"{row['tipo_material']} - {row['descricao_grupo']}: "
                f"{int(row['qtd_itens_criticos'])} itens | "
                f"Custo: R$ {row['custo_total_critico']:,.2f}"
                .replace(",", "X").replace(".", ",").replace("X", ".")
            )

        detalhes = "<br>".join(detalhes_linhas)

    return {
        "nome": "Produtos com Estoque Críticos",
        "valor": total_criticos,
        "valor_anterior": None,
        "unidade": "itens",
        "cor": "card-green" if total_criticos > 0 else "card-green",
        "extra": (
            f"Custo total crítico: "
            f"R$ {custo_total_geral:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            + "<br>" + detalhes
        )
    }