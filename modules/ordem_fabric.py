from __future__ import annotations

import os
import pandas as pd
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = int(os.getenv("MYSQL_PORT") or 3306)
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")


def connect_to_mysql():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )


def get_kpi():
    conn = connect_to_mysql()

    query = """
        SELECT
            ordf.data_fechamento,
            ordf.qtde_produzida,
            ordf.status_of
        FROM ORDEM_FABRIC ordf
        JOIN PRODUTO p
            ON TRIM(IFNULL(ordf.produto, '')) = TRIM(IFNULL(p.codigo_produto_material, ''))
        WHERE ordf.status_of = 'F'
        AND ordf.data_fechamento IS NOT NULL
        AND TRIM(IFNULL(p.tipo_material, '')) IN ('FO', 'PI')
        AND NOT (
        (p.GP_codigo_grupo = 500 AND p.SGP_codigo_subgrupo = '003')
        OR p.GP_codigo_grupo IN (800, 801)
    )
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return {
            "nome": "Produção Kg", #alterado
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "un",
            "cor": "card-green",
            "volume_ultimo_dia": 0,
            "data_ultimo_dia": "",
        }

    df["data_fechamento"] = pd.to_datetime(df["data_fechamento"], errors="coerce")
    df["qtde_produzida"] = pd.to_numeric(df["qtde_produzida"], errors="coerce").fillna(0)
    df = df.dropna(subset=["data_fechamento"])

    hoje = pd.Timestamp.today().normalize()
    inicio_mes = hoje.replace(day=1)
    inicio_prox_mes = (inicio_mes + pd.DateOffset(months=1)).normalize()
    inicio_mes_anterior = (inicio_mes - pd.DateOffset(months=1)).normalize()

    df_mes = df[
        (df["data_fechamento"] >= inicio_mes) &
        (df["data_fechamento"] < inicio_prox_mes)
    ]

    df_mes_anterior = df[
        (df["data_fechamento"] >= inicio_mes_anterior) &
        (df["data_fechamento"] < inicio_mes)
    ]

    volume_mes = float(df_mes["qtde_produzida"].sum()) if not df_mes.empty else 0.0
    volume_mes_anterior = float(df_mes_anterior["qtde_produzida"].sum()) if not df_mes_anterior.empty else 0.0

    volume_ultimo_dia = 0.0
    data_ultimo_dia = ""

    if not df_mes.empty:
        df_mes = df_mes.copy()
        df_mes["dia_fechamento"] = df_mes["data_fechamento"].dt.date
        ultimo_dia = df_mes["dia_fechamento"].max()
        df_ultimo_dia = df_mes[df_mes["dia_fechamento"] == ultimo_dia]
        volume_ultimo_dia = float(df_ultimo_dia["qtde_produzida"].sum())
        data_ultimo_dia = pd.to_datetime(ultimo_dia).strftime("%d/%m/%Y")

    return {
        "nome": "Produção Kg",
        "valor": volume_mes,
        "valor_anterior": volume_mes_anterior,
        "unidade": "un",
        "cor": "card-green",
        "volume_ultimo_dia": volume_ultimo_dia,
        "data_ultimo_dia": data_ultimo_dia,
        "extra_obs": "A Qtde em Kg produzida desconsidera Gr/Sugr 500/003 e Gr 800 e 801."
    }

def get_kpi_of_abertas_997():
    conn = connect_to_mysql()

    query = """
        SELECT
            numero_da_of,
            data_abertura,
            produto,
            vlr_requisicoes,
            status_of,
            origem
        FROM ORDEM_FABRIC
        WHERE origem = 997
          AND data_abertura IS NOT NULL
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return {
            "nome": "OFs Abertas Mês 997",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-purple",
            "qtd_ofs_mes": 0,
            "qtd_lb_mes": 0,
            "qtd_cam_mes": 0,
            "qtd_status_a_mes": 0,
            "vlr_lb_mes": 0,
            "vlr_cam_mes": 0,
        }

    df["data_abertura"] = pd.to_datetime(df["data_abertura"], errors="coerce")
    df["vlr_requisicoes"] = pd.to_numeric(df["vlr_requisicoes"], errors="coerce").fillna(0)
    df["produto"] = df["produto"].fillna("").astype(str).str.strip().str.upper()
    df["status_of"] = df["status_of"].fillna("").astype(str).str.strip().str.upper()

    df = df.dropna(subset=["data_abertura"]).copy()

    if df.empty:
        return {
            "nome": "OFs Abertas Mês 997",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-purple",
            "qtd_ofs_mes": 0,
            "qtd_lb_mes": 0,
            "qtd_cam_mes": 0,
            "qtd_status_a_mes": 0,
            "vlr_lb_mes": 0,
            "vlr_cam_mes": 0,
        }

    # classifica pelo início do produto
    df["familia"] = df["produto"].apply(
        lambda x: "LB" if x.startswith("LB") else ("CAM" if x.startswith("CAM") else "OUTROS")
    )

    hoje = pd.Timestamp.today().normalize()
    inicio_mes = hoje.replace(day=1)
    inicio_prox_mes = (inicio_mes + pd.DateOffset(months=1)).normalize()
    inicio_mes_anterior = (inicio_mes - pd.DateOffset(months=1)).normalize()

    df_mes = df[
        (df["data_abertura"] >= inicio_mes) &
        (df["data_abertura"] < inicio_prox_mes)
    ].copy()

    df_mes_anterior = df[
        (df["data_abertura"] >= inicio_mes_anterior) &
        (df["data_abertura"] < inicio_mes)
    ].copy()

    valor_mes = float(df_mes["vlr_requisicoes"].sum()) if not df_mes.empty else 0.0
    valor_mes_anterior = float(df_mes_anterior["vlr_requisicoes"].sum()) if not df_mes_anterior.empty else 0.0

    qtd_ofs_mes = int(df_mes["numero_da_of"].nunique()) if not df_mes.empty else 0
    qtd_lb_mes = int(df_mes.loc[df_mes["familia"] == "LB", "numero_da_of"].nunique()) if not df_mes.empty else 0
    qtd_cam_mes = int(df_mes.loc[df_mes["familia"] == "CAM", "numero_da_of"].nunique()) if not df_mes.empty else 0
    qtd_status_a_mes = int(df_mes.loc[df_mes["status_of"] == "A", "numero_da_of"].nunique()) if not df_mes.empty else 0

    vlr_lb_mes = float(df_mes.loc[df_mes["familia"] == "LB", "vlr_requisicoes"].sum()) if not df_mes.empty else 0.0
    vlr_cam_mes = float(df_mes.loc[df_mes["familia"] == "CAM", "vlr_requisicoes"].sum()) if not df_mes.empty else 0.0

    return {
        "nome": "OFs Abertas Mês 997",
        "valor": valor_mes,
        "valor_anterior": valor_mes_anterior,
        "unidade": "R$",
        "cor": "card-purple",
        "qtd_ofs_mes": qtd_ofs_mes,
        "qtd_lb_mes": qtd_lb_mes,
        "qtd_cam_mes": qtd_cam_mes,
        "qtd_status_a_mes": qtd_status_a_mes,
        "vlr_lb_mes": vlr_lb_mes,
        "vlr_cam_mes": vlr_cam_mes,
        "extra_obs": "A Qtde em Kg produzida desconsidera Gr/Sugr 500/003 e Gr 800 e 801."
    }

def get_kpi_of_atrasadas():
    conn = connect_to_mysql()

    query = """
        SELECT
            numero_da_of,
            data_abertura,
            data_fechamento,
            data_prev_entrega,
            status_of,
            origem
        FROM ORDEM_FABRIC
        WHERE status_of = 'A'
        AND data_prev_entrega IS NOT NULL
        AND origem <> 997
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return {
            "nome": "OFs Atrasadas",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "un",
            "cor": "card-pink",
            "faixa_2_5": 0,
            "faixa_6_10": 0,
            "faixa_acima_10": 0,
        }

    df["data_prev_entrega"] = pd.to_datetime(df["data_prev_entrega"], errors="coerce")
    df["data_abertura"] = pd.to_datetime(df["data_abertura"], errors="coerce")
    df["data_fechamento"] = pd.to_datetime(df["data_fechamento"], errors="coerce")

    df = df.dropna(subset=["data_prev_entrega"]).copy()

    hoje = pd.Timestamp.today().normalize()

    df["dias_atraso"] = (hoje - df["data_prev_entrega"].dt.normalize()).dt.days

    # somente OFs realmente atrasadas
    df_atrasadas = df[df["dias_atraso"] >= 2].copy()

    if df_atrasadas.empty:
        return {
            "nome": "OFs Atrasadas",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "un",
            "cor": "card-pink",
            "faixa_2_5": 0,
            "faixa_6_10": 0,
            "faixa_acima_10": 0,
        }

    # evita duplicidade por numero_da_of
    df_atrasadas = (
        df_atrasadas
        .sort_values(["numero_da_of", "data_prev_entrega"])
        .drop_duplicates(subset=["numero_da_of"], keep="last")
    )

    faixa_2_5 = int(df_atrasadas["dias_atraso"].between(2, 5).sum())
    faixa_6_10 = int(df_atrasadas["dias_atraso"].between(6, 10).sum())
    faixa_acima_10 = int((df_atrasadas["dias_atraso"] > 10).sum())

    total_atrasadas = int(df_atrasadas["numero_da_of"].nunique())

    # comparação simples com o dia anterior
    ontem = hoje - pd.Timedelta(days=1)
    df["dias_atraso_ontem"] = (ontem - df["data_prev_entrega"].dt.normalize()).dt.days
    df_atrasadas_ontem = df[df["dias_atraso_ontem"] >= 2].copy()
    if not df_atrasadas_ontem.empty:
        df_atrasadas_ontem = (
            df_atrasadas_ontem
            .sort_values(["numero_da_of", "data_prev_entrega"])
            .drop_duplicates(subset=["numero_da_of"], keep="last")
        )
        total_ontem = int(df_atrasadas_ontem["numero_da_of"].nunique())
    else:
        total_ontem = 0

    return {
        "nome": "OFs Atrasadas",
        "valor": total_atrasadas,
        "valor_anterior": total_ontem,
        "unidade": "un",
        "cor": "card-pink",
        "faixa_2_5": faixa_2_5,
        "faixa_6_10": faixa_6_10,
        "faixa_acima_10": faixa_acima_10,
        "extra_obs": "As Ofs atrasada não estão desconsiderando 997 ou 999"
    }
