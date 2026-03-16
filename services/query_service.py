import pandas as pd
import streamlit as st
from database import get_connection

@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    conn = None
    try:
        conn = get_connection()
        return pd.read_sql(sql, conn)
    except Exception as e:
        st.error(f"Erro ao executar consulta: {e}")
        return pd.DataFrame()
    finally:
        if conn is not None and conn.is_connected():
            conn.close()
# import pandas as pd
# from database import get_connection

# def run_query(sql: str) -> pd.DataFrame:
#     conn = get_connection()
#     return pd.read_sql(sql, conn)
