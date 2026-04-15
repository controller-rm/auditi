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
            data_abertura,
            cod_historico,
            custo_total,
            numero_da_of
        FROM REQUISICOES
        WHERE cod_historico IN (30, 22, 999)
          AND data_abertura IS NOT NULL
    """

    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return {
            "nome": "Correções",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-pink",
            "valor_ultimo_dia": 0,
            "data_ultimo_dia": "Sem movimento",
            "qtd_ofs_mes": 0,
        }

    df["data_abertura"] = pd.to_datetime(df["data_abertura"], errors="coerce")
    df["custo_total"] = pd.to_numeric(df["custo_total"], errors="coerce").fillna(0)
    df = df.dropna(subset=["data_abertura"]).copy()

    if df.empty:
        return {
            "nome": "Correções",
            "valor": 0,
            "valor_anterior": 0,
            "unidade": "R$",
            "cor": "card-pink",
            "valor_ultimo_dia": 0,
            "data_ultimo_dia": "Sem movimento",
            "qtd_ofs_mes": 0,
        }

    hoje = pd.Timestamp.today().normalize()

    inicio_mes_atual = hoje.replace(day=1)
    inicio_proximo_mes = inicio_mes_atual + pd.DateOffset(months=1)
    inicio_mes_anterior = inicio_mes_atual - pd.DateOffset(months=1)

    df_mes_atual = df[
        (df["data_abertura"] >= inicio_mes_atual) &
        (df["data_abertura"] < inicio_proximo_mes)
    ].copy()

    df_mes_anterior = df[
        (df["data_abertura"] >= inicio_mes_anterior) &
        (df["data_abertura"] < inicio_mes_atual)
    ].copy()

    valor_mes_atual = float(df_mes_atual["custo_total"].sum()) if not df_mes_atual.empty else 0.0
    valor_mes_anterior = float(df_mes_anterior["custo_total"].sum()) if not df_mes_anterior.empty else 0.0

    valor_ultimo_dia = 0.0
    data_ultimo_dia = "Sem movimento"

    if not df_mes_atual.empty:
        df_mes_atual["dia_abertura"] = df_mes_atual["data_abertura"].dt.date
        ultimo_dia = df_mes_atual["dia_abertura"].max()

        df_ultimo_dia = df_mes_atual[df_mes_atual["dia_abertura"] == ultimo_dia].copy()
        valor_ultimo_dia = float(df_ultimo_dia["custo_total"].sum())
        data_ultimo_dia = pd.to_datetime(ultimo_dia).strftime("%d/%m/%Y")

    qtd_ofs_mes = int(df_mes_atual["numero_da_of"].nunique()) if not df_mes_atual.empty else 0

    return {
        "nome": "Correções",
        "valor": valor_mes_atual,
        "valor_anterior": valor_mes_anterior,
        "unidade": "R$",
        "cor": "card-pink",
        "valor_ultimo_dia": valor_ultimo_dia,
        "data_ultimo_dia": data_ultimo_dia,
        "qtd_ofs_mes": qtd_ofs_mes,
        "extra_obs": "Estou considerando as requisições com historico 30,22 e 999"
    }
