import pandas as pd
import streamlit as st
from services.query_service import run_query


SQL_COMPRAS_PENDENTES = """
SELECT
    COUNT(DISTINCT oc.numero_oc) AS total_oc_pendentes,
    COUNT(*) AS total_itens_pendentes,
    COALESCE(SUM(GREATEST(ioc.quantidade_comprada - ioc.quantidade_atendida, 0)), 0) AS quantidade_pendente,
    COALESCE(SUM(GREATEST(ioc.quantidade_comprada - ioc.quantidade_atendida, 0) * ioc.valor_unitario), 0) AS valor_pendente
FROM ORDEM_COMPRA oc
INNER JOIN ITENS_ORDEM_COMPRA ioc
    ON oc.numero_oc = ioc.numero_oc
LEFT JOIN PRODUTO p
    ON p.codigo_produto_material = ioc.codigo_material
WHERE oc.situacao_oc = 'A'
  AND ioc.status_item IN ('ATP', 'PEN')
  AND GREATEST(ioc.quantidade_comprada - ioc.quantidade_atendida, 0) > 0
"""


SQL_COMPRAS_PENDENTES_TIPO = """
SELECT
    COALESCE(p.tipo_material, 'SEM TIPO') AS tipo_material,
    COUNT(*) AS total_itens_pendentes,
    COALESCE(SUM(GREATEST(ioc.quantidade_comprada - ioc.quantidade_atendida, 0)), 0) AS quantidade_pendente,
    COALESCE(SUM(GREATEST(ioc.quantidade_comprada - ioc.quantidade_atendida, 0) * ioc.valor_unitario), 0) AS valor_pendente
FROM ORDEM_COMPRA oc
INNER JOIN ITENS_ORDEM_COMPRA ioc
    ON oc.numero_oc = ioc.numero_oc
LEFT JOIN PRODUTO p
    ON p.codigo_produto_material = ioc.codigo_material
WHERE oc.situacao_oc = 'A'
  AND ioc.status_item IN ('ATP', 'PEN')
  AND GREATEST(ioc.quantidade_comprada - ioc.quantidade_atendida, 0) > 0
GROUP BY COALESCE(p.tipo_material, 'SEM TIPO')
ORDER BY valor_pendente DESC
"""


def formatar_moeda_br(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def get_kpi():
    try:
        df = run_query(SQL_COMPRAS_PENDENTES)
        df_tipo = run_query(SQL_COMPRAS_PENDENTES_TIPO)

        valor_pendente = float(df.iloc[0]["valor_pendente"] or 0)
        total_oc_pendentes = int(df.iloc[0]["total_oc_pendentes"] or 0)
        total_itens_pendentes = int(df.iloc[0]["total_itens_pendentes"] or 0)

        detalhes_tipo = ""
        if df_tipo is not None and not df_tipo.empty:
            linhas = []
            for _, row in df_tipo.iterrows():
                linhas.append(
                    f"{row['tipo_material']}: {formatar_moeda_br(float(row['valor_pendente'] or 0))}"
                )
            detalhes_tipo = " | ".join(linhas)

        extra = (
            f"{total_oc_pendentes} OCs | "
            f"{total_itens_pendentes} itens"
        )

        if detalhes_tipo:
            extra += f"<br>{detalhes_tipo}"

        return {
            "nome": "Compras Pendentes",
            "valor": valor_pendente,
            "valor_anterior": valor_pendente,
            "unidade": "R$",
            "cor": "card-purple",
            "qtd_ordens": total_oc_pendentes,
            "qtd_itens": total_itens_pendentes,
            "extra": extra,
        }

    except Exception as e:
        st.error(f"Erro no módulo Compras Pendentes: {e}")
        return {
            "nome": "Compras Pendentes",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-purple",
            "qtd_ordens": 0,
            "qtd_itens": 0,
            "extra": "",
        }


def get_detalhe():
    try:
        df = run_query(SQL_COMPRAS_PENDENTES)

        if df.empty:
            return {
                "total_oc_pendentes": 0,
                "total_itens_pendentes": 0,
                "quantidade_pendente": 0.0,
                "valor_pendente": 0.0,
            }

        row = df.iloc[0]
        return {
            "total_oc_pendentes": int(row["total_oc_pendentes"] or 0),
            "total_itens_pendentes": int(row["total_itens_pendentes"] or 0),
            "quantidade_pendente": float(row["quantidade_pendente"] or 0),
            "valor_pendente": float(row["valor_pendente"] or 0),
        }
    except Exception:
        return {
            "total_oc_pendentes": 0,
            "total_itens_pendentes": 0,
            "quantidade_pendente": 0.0,
            "valor_pendente": 0.0,
        }


def get_resumo_por_tipo_material():
    try:
        df = run_query(SQL_COMPRAS_PENDENTES_TIPO)

        if df is None or df.empty:
            return pd.DataFrame(
                columns=[
                    "tipo_material",
                    "total_itens_pendentes",
                    "quantidade_pendente",
                    "valor_pendente",
                ]
            )

        return df

    except Exception as e:
        st.error(f"Erro ao gerar resumo por tipo de material: {e}")
        return pd.DataFrame(
            columns=[
                "tipo_material",
                "total_itens_pendentes",
                "quantidade_pendente",
                "valor_pendente",
            ]
        )


def get_serie_mensal():
    return pd.DataFrame(columns=["Mês", "Valor"])