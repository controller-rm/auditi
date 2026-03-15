import pandas as pd
import streamlit as st
from database import get_connection

@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    return pd.read_sql(sql, conn)

# import pandas as pd
# from database import get_connection

# def run_query(sql: str) -> pd.DataFrame:
#     conn = get_connection()
#     return pd.read_sql(sql, conn)