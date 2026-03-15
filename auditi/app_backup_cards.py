from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules import (
    faturamento,
    estoque,
    pedidos,
    financeiro,
    compras_pendentes,
    pedidos_mes,
    OF_dispersao,
    cq_liberacao,
    ordem_fabric,
    correcoes,
    margem,
    areceber,
    entradas,
)

# =========================================================
# CONFIGURAÇÃO DA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Auditi | Painel Gerencial",
    page_icon="📊",
    layout="wide",
)

# =========================================================
# ESTILO
# =========================================================
st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1rem;
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 100%;
        }

        .main-title {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.2rem;
            white-space: normal;
            overflow: visible;
            line-height: 1.2;
        }

        .sub-title {
            color: #5b6470;
            margin-bottom: 1.2rem;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin-top: 0.2rem;
            margin-bottom: 0.8rem;
        }

        .sector-header {
            background: #eef2f7;
            border-left: 5px solid #1d4ed8;
            border-radius: 10px;
            padding: 10px 12px;
            font-weight: 700;
            font-size: 1rem;
            color: #1e293b;
            margin-bottom: 12px;
        }

        .metric-card {
            border-radius: 16px;
            padding: 16px 18px;
            min-height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            color: #102027;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.05);
            margin-bottom: 12px;
        }

        .metric-title {
            font-size: 0.95rem;
            font-weight: 600;
            color: #334155;
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 1.9rem;
            font-weight: 800;
            line-height: 1.1;
        }

        .metric-footer {
            display: flex;
            justify-content: space-between;
            align-items: end;
            gap: 10px;
        }

        .metric-delta {
            font-size: 0.85rem;
            font-weight: 600;
        }

        .metric-extra {
            font-size: 0.78rem;
            font-weight: 600;
            color: #334155;
            text-align: right;
            white-space: normal;
            line-height: 1.4;
        }

        .card-green { background: #dff3e7; }
        .card-yellow { background: #fff3cd; }
        .card-blue { background: #dbeafe; }
        .card-pink { background: #f8d7da; }
        .card-purple { background: #ebe3ff; }

        .chart-box {
            background: white;
            border-radius: 16px;
            padding: 10px 12px 6px 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            border: 1px solid rgba(0,0,0,0.05);
        }

        .footer-note {
            margin-top: 1rem;
            color: #667085;
            font-size: 0.9rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# MODELO
# =========================================================
@dataclass
class AreaIndicador:
    nome: str
    valor: float
    valor_anterior: float
    unidade: str
    cor: str
    extra: Optional[str] = None

    @property
    def delta_perc(self) -> float:
        if self.valor_anterior == 0:
            return 0.0
        return ((self.valor - self.valor_anterior) / self.valor_anterior) * 100


def formatar_numero(valor: float, unidade: str) -> str:
    if unidade == "R$":
        texto = f"R$ {valor:,.2f}"
        return texto.replace(",", "X").replace(".", ",").replace("X", ".")
    if unidade == "dias":
        return f"{valor:.1f} dias".replace(".", ",")
    if unidade == "%":
        return f"{valor:.2f}%".replace(".", ",")
    return f"{valor:,.0f}".replace(",", ".")

def delta_texto(delta: float) -> str:
    seta = "▲" if delta >= 0 else "▼"
    return f"{seta} {abs(delta):.1f}% vs mês anterior"


# =========================================================
# DADOS DOS MÓDULOS
# =========================================================
kpi_faturamento = faturamento.get_kpi()
kpi_pedidos = pedidos.get_kpi()
kpi_financeiro = financeiro.get_kpi()
kpi_estoque = estoque.get_kpi()
kpi_compras_pendentes = compras_pendentes.get_kpi()
kpi_pedidos_mes = pedidos_mes.get_kpi()
kpi_prazo_entrega = pedidos_mes.get_kpi_prazo_medio_entrega()
kpi_of_dispersao = OF_dispersao.get_kpi()
kpi_cq_liberacao = cq_liberacao.get_kpi()
kpi_producao = ordem_fabric.get_kpi()
kpi_of_atrasadas = ordem_fabric.get_kpi_of_atrasadas()
kpi_correcoes = correcoes.get_kpi()
kpi_of_abertas_997 = ordem_fabric.get_kpi_of_abertas_997()
kpi_margem = margem.get_kpi()
kpi_areceber = areceber.get_kpi()
kpi_estoque_avaria = estoque.get_kpi_avarias()
kpi_entradas = entradas.get_kpi()

# =========================================================
# ORGANIZAÇÃO POR SETOR
# =========================================================
setores = {
    "Comercial": [
        AreaIndicador(
            nome=kpi_faturamento["nome"],
            valor=kpi_faturamento["valor"],
            valor_anterior=kpi_faturamento["valor_anterior"],
            unidade=kpi_faturamento["unidade"],
            cor=kpi_faturamento["cor"],
            extra=None,
        ),
        AreaIndicador(
            nome=kpi_margem["nome"],
            valor=kpi_margem["valor"],
            valor_anterior=kpi_margem["valor_anterior"],
            unidade=kpi_margem["unidade"],
            cor=kpi_margem["cor"],
            extra=(
                f'Mês: {formatar_numero(kpi_margem.get("total_margem_mes", 0), "R$")} | '
                f'Mês ant.: {formatar_numero(kpi_margem.get("total_margem_mes_anterior", 0), "R$")}<br>'
                f'Último dia: {formatar_numero(kpi_margem.get("total_margem_ultimo_dia", 0), "R$")} | '
                f'{kpi_margem.get("data_ultimo_dia", "")}'
            )
        ),
        AreaIndicador(**kpi_pedidos),
        AreaIndicador(
            nome=kpi_pedidos_mes["nome"],
            valor=kpi_pedidos_mes["valor"],
            valor_anterior=kpi_pedidos_mes["valor_anterior"],
            unidade=kpi_pedidos_mes["unidade"],
            cor=kpi_pedidos_mes["cor"],
            extra=f'{kpi_pedidos_mes.get("qtd_pedidos", 0)} pedidos no mês'
        ),
        AreaIndicador(
            nome=kpi_prazo_entrega["nome"],
            valor=kpi_prazo_entrega["valor"],
            valor_anterior=kpi_prazo_entrega["valor_anterior"],
            unidade=kpi_prazo_entrega["unidade"],
            cor=kpi_prazo_entrega["cor"],
            extra=(
                f'Até 2d: {kpi_prazo_entrega.get("qtd_ate_2", 0)} | '
                f'Até 5d: {kpi_prazo_entrega.get("qtd_ate_5", 0)}<br>'
                f'Até 8d: {kpi_prazo_entrega.get("qtd_ate_8", 0)} | '
                f'>8d: {kpi_prazo_entrega.get("qtd_maior_8", 0)}'
            )
        ),
    ],
    "Produção": [
        AreaIndicador(
            nome=kpi_of_dispersao["nome"],
            valor=kpi_of_dispersao["valor"],
            valor_anterior=kpi_of_dispersao["valor_anterior"],
            unidade=kpi_of_dispersao["unidade"],
            cor=kpi_of_dispersao["cor"],
            extra=(
                f'{kpi_of_dispersao.get("qtd_apontamentos", 0)} dispersões | '
                f'{int(kpi_of_dispersao.get("qtde_produzida_total", 0)):,} produzida'
            ).replace(",", ".")
        ),
        AreaIndicador(
            nome=kpi_producao["nome"],
            valor=kpi_producao["valor"],
            valor_anterior=kpi_producao["valor_anterior"],
            unidade=kpi_producao["unidade"],
            cor=kpi_producao["cor"],
            extra=(
                f'{int(kpi_producao.get("volume_ultimo_dia", 0)):,} no último dia | '
                f'{kpi_producao.get("data_ultimo_dia", "Sem produção")}'
            ).replace(",", ".")
        ),
        AreaIndicador(
            nome=kpi_of_atrasadas["nome"],
            valor=kpi_of_atrasadas["valor"],
            valor_anterior=kpi_of_atrasadas["valor_anterior"],
            unidade=kpi_of_atrasadas["unidade"],
            cor=kpi_of_atrasadas["cor"],
            extra=(
                f'2-5d: {kpi_of_atrasadas.get("faixa_2_5", 0)} | '
                f'6-10d: {kpi_of_atrasadas.get("faixa_6_10", 0)} | '
                f'>10d: {kpi_of_atrasadas.get("faixa_acima_10", 0)}'
            )
        ),

        AreaIndicador(
            nome=kpi_correcoes["nome"],
            valor=kpi_correcoes["valor"],
            valor_anterior=kpi_correcoes["valor_anterior"],
            unidade=kpi_correcoes["unidade"],
            cor=kpi_correcoes["cor"],
            extra=(
                f'Mês ant.: {formatar_numero(kpi_correcoes.get("valor_anterior", 0), "R$")}<br>'
                f'{kpi_correcoes.get("qtd_ofs_mes", 0)} OFs | '
                f'Último dia: {formatar_numero(kpi_correcoes.get("valor_ultimo_dia", 0), "R$")}'
            )
        ),

        
    ],
    "Laboratório": [
        AreaIndicador(
            nome=kpi_cq_liberacao["nome"],
            valor=kpi_cq_liberacao["valor"],
            valor_anterior=kpi_cq_liberacao["valor_anterior"],
            unidade=kpi_cq_liberacao["unidade"],
            cor=kpi_cq_liberacao["cor"],
            extra=f'{kpi_cq_liberacao.get("total_of_mes", 0)} OFs no mês'
        ),
        AreaIndicador(
            nome=kpi_of_abertas_997["nome"],
            valor=kpi_of_abertas_997["valor"],
            valor_anterior=kpi_of_abertas_997["valor_anterior"],
            unidade=kpi_of_abertas_997["unidade"],
            cor=kpi_of_abertas_997["cor"],
            extra=(
                f'OFs: {kpi_of_abertas_997.get("qtd_ofs_mes", 0)} | '
                f'Abertas: {kpi_of_abertas_997.get("qtd_status_a_mes", 0)}<br>'
                f'LB: {kpi_of_abertas_997.get("qtd_lb_mes", 0)} '
                f'({formatar_numero(kpi_of_abertas_997.get("vlr_lb_mes", 0), "R$")}) | '
                f'CAM: {kpi_of_abertas_997.get("qtd_cam_mes", 0)} '
                f'({formatar_numero(kpi_of_abertas_997.get("vlr_cam_mes", 0), "R$")})'
            )
        ),
    ],
    "Suprimentos": [
        AreaIndicador(**kpi_estoque),
        AreaIndicador(**kpi_estoque_avaria),
        AreaIndicador(
            nome=kpi_compras_pendentes["nome"],
            valor=kpi_compras_pendentes["valor"],
            valor_anterior=kpi_compras_pendentes["valor_anterior"],
            unidade=kpi_compras_pendentes["unidade"],
            cor=kpi_compras_pendentes["cor"],
            extra=(
                f'{kpi_compras_pendentes.get("qtd_ordens", 0)} ordens | '
                f'{kpi_compras_pendentes.get("qtd_itens", 0)} itens'
            )
        ),
        AreaIndicador(
            nome=kpi_entradas["nome"],
            valor=kpi_entradas["valor"],
            valor_anterior=kpi_entradas["valor_anterior"],
            unidade=kpi_entradas["unidade"],
            cor=kpi_entradas["cor"],
            extra=kpi_entradas["extra"]
        ),
    ],
    
    "Financeiro": [
        AreaIndicador(
            nome=kpi_financeiro["nome"],
            valor=kpi_financeiro["valor"],
            valor_anterior=kpi_financeiro["valor_anterior"],
            unidade=kpi_financeiro["unidade"],
            cor=kpi_financeiro["cor"],
            extra=(
                f'Venc.: {formatar_numero(kpi_financeiro.get("total_vencido", 0), "R$")}<br>títulos<br> '
                f'A vencer: {formatar_numero(kpi_financeiro.get("total_a_vencer", 0), "R$")}<br>'
                f'Juros: {formatar_numero(kpi_financeiro.get("juros_pagos_mes", 0), "R$")} | '
                f'{kpi_financeiro.get("qtd_titulos_vencidos", 0)} venc. / '
                f'{kpi_financeiro.get("qtd_titulos_a_vencer", 0)} a vencer'
            )
        ),
        AreaIndicador(
            nome=kpi_areceber["nome"],
            valor=kpi_areceber["valor"],
            valor_anterior=kpi_areceber["valor_anterior"],
            unidade=kpi_areceber["unidade"],
            cor=kpi_areceber["cor"],
            extra=(
                f'A receber: {formatar_numero(kpi_areceber.get("valor_a_receber", 0), "R$")} | '
                f'{kpi_areceber.get("qtd_titulos", 0)} títulos<br>'
                f'Desc.: {formatar_numero(kpi_areceber.get("desconto_concedido_mes", 0), "R$")} | '
                f'Juros: {formatar_numero(kpi_areceber.get("juros_cobrado_mes", 0), "R$")}<br>'
                f'Venc.: {formatar_numero(kpi_areceber.get("valor_vencido", 0), "R$")} | '
                f'A vencer: {formatar_numero(kpi_areceber.get("valor_a_vencer", 0), "R$")}<br>'
                f'{kpi_areceber.get("qtd_titulos_vencidos", 0)} venc. / '
                f'{kpi_areceber.get("qtd_titulos_a_vencer", 0)} a vencer'
            )
        ),
    ],
}

todas_areas = [area for lista in setores.values() for area in lista]

# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("Auditi")
st.sidebar.caption("Painel executivo por setor")

# =========================================================
# CABEÇALHO
# =========================================================
st.title("Auditi | Painel de Indicadores")
st.markdown(
    '<div class="sub-title">Resumo mensal das áreas da empresa com visão gerencial e indicadores integrados ao banco de dados.</div>',
    unsafe_allow_html=True,
)

# =========================================================
# FUNÇÕES DE GRÁFICOS
# =========================================================
def grafico_linha(df: pd.DataFrame, titulo: str) -> go.Figure:
    if df.empty:
        fig = go.Figure()
        fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
        return fig

    fig = px.line(df, x="Mês", y="Valor", markers=True)
    fig.update_layout(
        title=titulo,
        margin=dict(l=10, r=10, t=35, b=10),
        height=260,
        xaxis_title=None,
        yaxis_title=None,
        showlegend=False,
    )
    return fig


def grafico_donut_setores() -> go.Figure:
    nomes = []
    valores = []

    for nome_setor, indicadores in setores.items():
        total_setor = sum(max(ind.valor, 0) for ind in indicadores)
        nomes.append(nome_setor)
        valores.append(total_setor)

    fig = go.Figure(
        data=[
            go.Pie(
                labels=nomes,
                values=valores,
                hole=0.6,
                textinfo="percent",
            )
        ]
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=320,
        showlegend=True,
    )

    return fig


# =========================================================
# INDICADORES POR SETOR EM COLUNAS
# =========================================================
st.markdown('<div class="section-title">Indicadores por setor</div>', unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

colunas_setores = {
    "Comercial": col1,
    "Produção": col2,
    "Laboratório": col3,
    "Suprimentos": col4,
    "Financeiro": col5,
}

for nome_setor, indicadores in setores.items():
    with colunas_setores[nome_setor]:
        st.markdown(f'<div class="sector-header">{nome_setor}</div>', unsafe_allow_html=True)

        for area in indicadores:
            st.markdown(
                f"""
                <div class="metric-card {area.cor}">
                    <div>
                        <div class="metric-title">{area.nome}</div>
                        <div class="metric-value">{formatar_numero(area.valor, area.unidade)}</div>
                    </div>
                    <div class="metric-footer">
                        <div class="metric-delta">{delta_texto(area.delta_perc)}</div>
                        {"<div class='metric-extra'>" + area.extra + "</div>" if area.extra else "<div></div>"}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# =========================================================
# RESUMO + GRÁFICO GERAL
# =========================================================
col_left, col_right = st.columns([1.25, 1])

with col_left:
    st.markdown('<div class="section-title">Resumo executivo</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card card-green">
                <div class="metric-title">Setores monitorados</div>
                <div class="metric-value">{len(setores)}</div>
                <div class="metric-delta">Painel ativo</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card card-yellow">
                <div class="metric-title">Indicadores ativos</div>
                <div class="metric-value">{len(todas_areas)}</div>
                <div class="metric-delta">Cards carregados</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card card-blue">
                <div class="metric-title">Consultas executadas</div>
                <div class="metric-value">{len(todas_areas)}</div>
                <div class="metric-delta">Módulos carregados</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        eficiencia = 100 if all(a.valor >= 0 for a in todas_areas) else 0
        st.markdown(
            f"""
            <div class="metric-card card-pink">
                <div class="metric-title">Eficiência de carga</div>
                <div class="metric-value">{eficiencia:.1f}%</div>
                <div class="metric-delta">Base integrada</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    df_setores = pd.DataFrame(
        [
            {"Setor": setor, "Qtd Indicadores": len(indicadores)}
            for setor, indicadores in setores.items()
        ]
    )

    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.plotly_chart(
        px.bar(
            df_setores,
            x="Setor",
            y="Qtd Indicadores",
            text_auto=True,
            title="Quantidade de indicadores por setor"
        ),
        use_container_width=True,
        key="grafico_barras_setores",
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div class="section-title">Distribuição por setor</div>', unsafe_allow_html=True)
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    st.plotly_chart(
        grafico_donut_setores(),
        use_container_width=True,
        key="grafico_donut_setores",
    )
    st.markdown('</div>', unsafe_allow_html=True)

# =========================================================
# TABELA DETALHADA
# =========================================================
st.markdown('<div class="section-title">Base resumida dos indicadores</div>', unsafe_allow_html=True)

linhas = []
for nome_setor, indicadores in setores.items():
    for area in indicadores:
        linhas.append(
            {
                "Setor": nome_setor,
                "Indicador": area.nome,
                "Valor Atual": formatar_numero(area.valor, area.unidade),
                "Valor Anterior": formatar_numero(area.valor_anterior, area.unidade),
                "Variação %": f"{area.delta_perc:.2f}%",
            }
        )

st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

st.markdown(
    '<div class="footer-note">AUDITI organizado por setor, mantendo o visual executivo em colunas e distribuição de indicadores por área.</div>',
    unsafe_allow_html=True,
)
