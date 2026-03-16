from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time

def main(status_placeholder):
    import streamlit as st

    def render_status_topo(mensagem: str, tempo: float = 0.0, concluido: bool = False):
        classe = "status-topo-ok" if concluido else "status-topo"
        titulo = "✅ Informações processadas" if concluido else "⏳ Aguarde, estamos processando as informações..."

        status_placeholder.markdown(
            f"""
            <div class="{classe}">
                <div class="status-topo-titulo">{titulo}</div>
                <div class="status-topo-texto">
                    {mensagem}<br>
                    Tempo decorrido: <b>{tempo:.1f} s</b>
                </div>
            </div>
            """.replace(".", ","),
            unsafe_allow_html=True,
        )
    if not st.session_state.get("authenticated", False):
        st.error("Acesso não autorizado. Faça login primeiro.")
        st.stop()

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
        itemcritico,
        estrutura,
        reposicaoxmedio,
        meta,
        metaatingida,
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

            .diag-box {
                border-radius: 16px;
                padding: 14px 16px;
                margin-bottom: 12px;
                border: 1px solid rgba(0,0,0,0.06);
                box-shadow: 0 2px 10px rgba(0,0,0,0.04);
                background: white;
            }

            .diag-ok {
                background: #e8f7ec;
                border-left: 6px solid #16a34a;
            }

            .diag-warn {
                background: #fff8e1;
                border-left: 6px solid #d97706;
            }

            .diag-crit {
                background: #fdecec;
                border-left: 6px solid #dc2626;
            }

            .diag-title {
                font-size: 1rem;
                font-weight: 700;
                margin-bottom: 4px;
                color: #1e293b;
            }

            .diag-text {
                font-size: 0.92rem;
                color: #334155;
                line-height: 1.45;
                margin-bottom: 6px;
            }

            .diag-impact {
                font-size: 0.85rem;
                font-weight: 700;
                color: #475569;
                margin-top: 8px;
            }

            .diag-rec {
                font-size: 0.85rem;
                color: #0f172a;
                margin-top: 4px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================
    # MODELOS
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
        def delta_perc(self):
            try:
                if not self.valor_anterior:
                    return None
                return ((self.valor - self.valor_anterior) / self.valor_anterior) * 100
            except:
                return None


    @dataclass
    class DiagnosticoItem:
        titulo: str
        status: str   # Saudável | Atenção | Crítico
        mensagem: str
        impacto: str
        recomendacao: str


    @dataclass
    class DiagnosticoSetor:
        setor: str
        status: str
        resumo: str
        itens: List[DiagnosticoItem]


    # =========================================================
    # FUNÇÕES AUXILIARES
    # =========================================================
    def formatar_numero(valor: float, unidade: str) -> str:
        try:
            valor = float(valor or 0)
        except Exception:
            valor = 0.0

        if unidade == "R$":
            texto = f"R$ {valor:,.2f}"
            return texto.replace(",", "X").replace(".", ",").replace("X", ".")
        if unidade == "dias":
            return f"{valor:.1f} dias".replace(".", ",")
        if unidade == "%":
            return f"{valor:.2f}%".replace(".", ",")
        return f"{valor:,.0f}".replace(",", ".")


    def delta_texto(delta):
        if delta is None:
            return ""

        seta = "▲" if delta >= 0 else "▼"
        return f"{seta} {delta:.2f}%"


    def classe_status(status: str) -> str:
        mapa = {
            "Saudável": "diag-ok",
            "Atenção": "diag-warn",
            "Crítico": "diag-crit",
        }
        return mapa.get(status, "diag-warn")


    def emoji_status(status: str) -> str:
        mapa = {
            "Saudável": "🟢",
            "Atenção": "🟡",
            "Crítico": "🔴",
        }
        return mapa.get(status, "🟡")


    def render_diagnostico_box(diag: DiagnosticoSetor):
        st.markdown(
            f"""
            <div class="diag-box {classe_status(diag.status)}">
                <div class="diag-title">{emoji_status(diag.status)} Diagnóstico {diag.setor}</div>
                <div class="diag-text"><b>Status:</b> {diag.status}</div>
                <div class="diag-text">{diag.resumo}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for item in diag.itens:
            st.markdown(
                f"""
                <div class="diag-box {classe_status(item.status)}">
                    <div class="diag-title">{emoji_status(item.status)} {item.titulo}</div>
                    <div class="diag-text">{item.mensagem}</div>
                    <div class="diag-impact">Impacto: {item.impacto}</div>
                    <div class="diag-rec">Recomendação: {item.recomendacao}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


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


    def gerar_diagnosticos(
        kpi_faturamento: dict,
        kpi_pedidos: dict,
        kpi_financeiro: dict,
        kpi_estoque: dict,
        kpi_compras_pendentes: dict,
        kpi_prazo_entrega: dict,
        kpi_of_dispersao: dict,
        kpi_cq_liberacao: dict,
        kpi_producao: dict,
        kpi_of_atrasadas: dict,
        kpi_correcoes: dict,
        kpi_of_abertas_997: dict,
        kpi_margem: dict,
        kpi_areceber: dict,
        kpi_estoque_avaria: dict,
        kpi_entradas: dict,
    ) -> tuple[list[DiagnosticoSetor], DiagnosticoSetor]:
        diagnosticos: list[DiagnosticoSetor] = []

        # =========================
        # COMERCIAL
        # =========================
        itens_comercial: list[DiagnosticoItem] = []

        margem_atual = float(kpi_margem.get("valor", 0) or 0)
        pedidos_pendentes = float(kpi_pedidos.get("valor", 0) or 0)
        faturamento_mes = float(kpi_faturamento.get("valor", 0) or 0)
        prazo_faturamento = float(kpi_prazo_entrega.get("valor", 0) or 0)

        if margem_atual < 8:
            itens_comercial.append(DiagnosticoItem(
                titulo="Margem abaixo do ideal",
                status="Crítico",
                mensagem=f"A margem atual está em {margem_atual:.2f}%, indicando rentabilidade pressionada nas vendas.",
                impacto="Redução do lucro operacional.",
                recomendacao="Revisar preço, mix vendido, descontos e custo dos produtos de maior giro."
            ))
        elif margem_atual < 12:
            itens_comercial.append(DiagnosticoItem(
                titulo="Margem em atenção",
                status="Atenção",
                mensagem=f"A margem atual está em {margem_atual:.2f}%, em faixa de atenção.",
                impacto="Menor absorção de custos e despesas.",
                recomendacao="Acompanhar descontos, política comercial e custos dos itens vendidos."
            ))
        else:
            itens_comercial.append(DiagnosticoItem(
                titulo="Margem saudável",
                status="Saudável",
                mensagem=f"A margem atual está em {margem_atual:.2f}%, dentro de uma faixa favorável.",
                impacto="Boa sustentação da rentabilidade.",
                recomendacao="Manter monitoramento por linha de produto e vendedor."
            ))

        if faturamento_mes > 0:
            perc_pendentes = (pedidos_pendentes / faturamento_mes) * 100
            if perc_pendentes > 35:
                itens_comercial.append(DiagnosticoItem(
                    titulo="Carteira pendente elevada",
                    status="Atenção",
                    mensagem=f"Os pedidos pendentes representam {perc_pendentes:.1f}% do faturamento do mês.",
                    impacto="Pode indicar atraso de entrega ou gargalo na produção/expedição.",
                    recomendacao="Cruzar carteira pendente com estoque, programação e datas prometidas."
                ))

        if prazo_faturamento > 5:
            itens_comercial.append(DiagnosticoItem(
                titulo="Prazo médio de faturamento alto",
                status="Atenção",
                mensagem=f"O prazo médio está em {prazo_faturamento:.1f} dias.",
                impacto="Atraso na conversão do pedido em receita.",
                recomendacao="Analisar gargalos entre pedido, separação, faturamento e expedição."
            ))
        else:
            itens_comercial.append(DiagnosticoItem(
                titulo="Prazo de faturamento eficiente",
                status="Saudável",
                mensagem=f"O prazo médio está em {prazo_faturamento:.1f} dias, indicando boa velocidade operacional.",
                impacto="Melhora da experiência do cliente e giro comercial.",
                recomendacao="Manter acompanhamento por faixa de atraso."
            ))

        status_comercial = "Saudável"
        if any(i.status == "Crítico" for i in itens_comercial):
            status_comercial = "Crítico"
        elif any(i.status == "Atenção" for i in itens_comercial):
            status_comercial = "Atenção"

        diagnosticos.append(DiagnosticoSetor(
            setor="Comercial",
            status=status_comercial,
            resumo="Avalia rentabilidade, carteira pendente e velocidade de faturamento.",
            itens=itens_comercial
        ))

        # =========================
        # PRODUÇÃO
        # =========================
        itens_producao: list[DiagnosticoItem] = []

        of_dispersao = float(kpi_of_dispersao.get("valor", 0) or 0)
        of_atrasadas = float(kpi_of_atrasadas.get("valor", 0) or 0)
        valor_correcoes = float(kpi_correcoes.get("valor", 0) or 0)
        producao_mes = float(kpi_producao.get("valor", 0) or 0)

        if of_atrasadas > 50:
            itens_producao.append(DiagnosticoItem(
                titulo="OFs atrasadas em nível crítico",
                status="Crítico",
                mensagem=f"Foram identificadas {int(of_atrasadas)} OFs atrasadas no mês.",
                impacto="Risco de atraso ao cliente, perda de eficiência e aumento de custo.",
                recomendacao="Priorizar programação, revisar gargalos e listar OFs por idade de atraso."
            ))
        elif of_atrasadas > 20:
            itens_producao.append(DiagnosticoItem(
                titulo="OFs atrasadas em atenção",
                status="Atenção",
                mensagem=f"Foram identificadas {int(of_atrasadas)} OFs atrasadas no mês.",
                impacto="Atrasos parciais na produção e pressão na programação.",
                recomendacao="Separar OFs por motivo: falta material, fila, setup ou liberação."
            ))
        else:
            itens_producao.append(DiagnosticoItem(
                titulo="Atrasos controlados",
                status="Saudável",
                mensagem=f"O volume de OFs atrasadas está em {int(of_atrasadas)}.",
                impacto="Maior previsibilidade operacional.",
                recomendacao="Manter controle diário por prioridade."
            ))

        if of_dispersao > 150:
            itens_producao.append(DiagnosticoItem(
                titulo="Alta dispersão produtiva",
                status="Atenção",
                mensagem=f"A dispersão de OFs está em {int(of_dispersao)}, sugerindo fragmentação da produção.",
                impacto="Mais setups, perda de produtividade e menor fluidez.",
                recomendacao="Agrupar produção por família, máquina ou sequência operacional."
            ))

        if valor_correcoes > 50000:
            itens_producao.append(DiagnosticoItem(
                titulo="Correções elevadas",
                status="Crítico",
                mensagem=f"As correções somam {formatar_numero(valor_correcoes, 'R$')} no mês.",
                impacto="Indício de retrabalho, erro de processo ou inconsistência operacional.",
                recomendacao="Abrir análise de causa por OF, operador, etapa e motivo da correção."
            ))
        elif valor_correcoes > 15000:
            itens_producao.append(DiagnosticoItem(
                titulo="Correções em atenção",
                status="Atenção",
                mensagem=f"As correções somam {formatar_numero(valor_correcoes, 'R$')} no mês.",
                impacto="Pressão sobre custo e margem.",
                recomendacao="Monitorar origem das correções e atacar reincidências."
            ))

        if producao_mes <= 0:
            itens_producao.append(DiagnosticoItem(
                titulo="Produção sem volume",
                status="Crítico",
                mensagem="Não houve volume produtivo relevante no período analisado.",
                impacto="Comprometimento direto do faturamento futuro.",
                recomendacao="Validar consultas, apontamentos e situação das ordens."
            ))

        status_producao = "Saudável"
        if any(i.status == "Crítico" for i in itens_producao):
            status_producao = "Crítico"
        elif any(i.status == "Atenção" for i in itens_producao):
            status_producao = "Atenção"

        diagnosticos.append(DiagnosticoSetor(
            setor="Produção",
            status=status_producao,
            resumo="Avalia atraso de OFs, dispersão operacional, correções e volume produzido.",
            itens=itens_producao
        ))

        # =========================
        # LABORATÓRIO
        # =========================
        itens_lab: list[DiagnosticoItem] = []

        cq_liberado = float(kpi_cq_liberacao.get("valor", 0) or 0)
        of_abertas_997 = float(kpi_of_abertas_997.get("valor", 0) or 0)

        if of_abertas_997 > 7000:
            itens_lab.append(DiagnosticoItem(
                titulo="OFs abertas em 997 elevadas",
                status="Atenção",
                mensagem=f"O valor em OFs abertas 997 está em {formatar_numero(of_abertas_997, 'R$')}.",
                impacto="Possível acúmulo em processo, pendência técnica ou fila de liberação.",
                recomendacao="Analisar idade das OFs e pendências de laboratório/CQ."
            ))

        if cq_liberado < 10:
            itens_lab.append(DiagnosticoItem(
                titulo="Baixo volume de liberações",
                status="Atenção",
                mensagem=f"Foram registradas apenas {int(cq_liberado)} liberações.",
                impacto="Risco de retenção do fluxo produtivo.",
                recomendacao="Validar capacidade, fila e prioridade das liberações."
            ))
        else:
            itens_lab.append(DiagnosticoItem(
                titulo="Fluxo de liberação ativo",
                status="Saudável",
                mensagem=f"Foram registradas {int(cq_liberado)} liberações no período.",
                impacto="Suporte ao andamento das ordens em processo.",
                recomendacao="Monitorar tempo médio entre abertura, análise e liberação."
            ))

        status_lab = "Saudável"
        if any(i.status == "Crítico" for i in itens_lab):
            status_lab = "Crítico"
        elif any(i.status == "Atenção" for i in itens_lab):
            status_lab = "Atenção"

        diagnosticos.append(DiagnosticoSetor(
            setor="Laboratório",
            status=status_lab,
            resumo="Avalia liberações e concentração de OFs em processo/pendência.",
            itens=itens_lab
        ))

        # =========================
        # SUPRIMENTOS
        # =========================
        itens_suprimentos: list[DiagnosticoItem] = []

        estoque_total = float(kpi_estoque.get("valor", 0) or 0)
        estoque_avaria = float(kpi_estoque_avaria.get("valor", 0) or 0)
        compras_pend = float(kpi_compras_pendentes.get("valor", 0) or 0)
        entradas_mes = float(kpi_entradas.get("valor", 0) or 0)

        if estoque_total > 0:
            perc_estoque_ruim = (estoque_avaria / estoque_total) * 100
            if perc_estoque_ruim > 10:
                itens_suprimentos.append(DiagnosticoItem(
                    titulo="Estoque problemático elevado",
                    status="Crítico",
                    mensagem=f"O estoque em avaria/vencido/não conforme representa {perc_estoque_ruim:.1f}% do estoque total.",
                    impacto="Capital parado, perda potencial e risco de baixa.",
                    recomendacao="Criar plano de ação por depósito: AVARIA, VENC e N CONF."
                ))
            elif perc_estoque_ruim > 5:
                itens_suprimentos.append(DiagnosticoItem(
                    titulo="Estoque problemático em atenção",
                    status="Atenção",
                    mensagem=f"O estoque em avaria/vencido/não conforme representa {perc_estoque_ruim:.1f}% do estoque total.",
                    impacto="Pressão sobre giro e qualidade do estoque.",
                    recomendacao="Acompanhar itens críticos e revisar tratativas de armazenagem."
                ))

        if entradas_mes > 0:
            relacao_pendente = compras_pend / entradas_mes
            if relacao_pendente > 3:
                itens_suprimentos.append(DiagnosticoItem(
                    titulo="Compras pendentes muito altas",
                    status="Crítico",
                    mensagem=f"As compras pendentes equivalem a {relacao_pendente:.1f} vezes as entradas do mês.",
                    impacto="Risco de sobrecarga futura, atraso ou desalinhamento de planejamento.",
                    recomendacao="Revisar backlog de compras por fornecedor, urgência e necessidade real."
                ))
            elif relacao_pendente > 1.5:
                itens_suprimentos.append(DiagnosticoItem(
                    titulo="Compras pendentes em atenção",
                    status="Atenção",
                    mensagem=f"As compras pendentes equivalem a {relacao_pendente:.1f} vezes as entradas do mês.",
                    impacto="Sinal de acúmulo ou atraso no abastecimento.",
                    recomendacao="Separar pendências por atraso, valor e impacto na produção."
                ))

        if not itens_suprimentos:
            itens_suprimentos.append(DiagnosticoItem(
                titulo="Suprimentos sem alertas relevantes",
                status="Saudável",
                mensagem="Não foram identificadas distorções relevantes nas regras atuais.",
                impacto="Fluxo de abastecimento aparentemente estável.",
                recomendacao="Manter análise por cobertura, giro e criticidade de materiais."
            ))

        status_supr = "Saudável"
        if any(i.status == "Crítico" for i in itens_suprimentos):
            status_supr = "Crítico"
        elif any(i.status == "Atenção" for i in itens_suprimentos):
            status_supr = "Atenção"

        diagnosticos.append(DiagnosticoSetor(
            setor="Suprimentos",
            status=status_supr,
            resumo="Avalia qualidade do estoque, backlog de compras e pressão de abastecimento.",
            itens=itens_suprimentos
        ))

        # =========================
        # FINANCEIRO
        # =========================
        itens_fin: list[DiagnosticoItem] = []

        pago_mes = float(kpi_financeiro.get("valor", 0) or 0)
        recebido_mes = float(kpi_areceber.get("valor", 0) or 0)
        valor_vencido = float(kpi_areceber.get("valor_vencido", 0) or 0)
        qtd_titulos_vencidos = float(kpi_areceber.get("qtd_titulos_vencidos", 0) or 0)

        saldo_caixa_operacional = recebido_mes - pago_mes
        if saldo_caixa_operacional < -300000:
            itens_fin.append(DiagnosticoItem(
                titulo="Pressão forte no caixa",
                status="Crítico",
                mensagem=f"O fluxo mensal mostra diferença negativa de {formatar_numero(abs(saldo_caixa_operacional), 'R$')} entre recebido e pago.",
                impacto="Maior necessidade de capital de giro.",
                recomendacao="Acelerar cobrança, renegociar prazos e revisar desembolsos relevantes."
            ))
        elif saldo_caixa_operacional < 0:
            itens_fin.append(DiagnosticoItem(
                titulo="Caixa em atenção",
                status="Atenção",
                mensagem=f"O fluxo mensal está negativo em {formatar_numero(abs(saldo_caixa_operacional), 'R$')}.",
                impacto="Pressão moderada no caixa.",
                recomendacao="Reforçar gestão de recebíveis e priorização de pagamentos."
            ))
        else:
            itens_fin.append(DiagnosticoItem(
                titulo="Fluxo mensal equilibrado",
                status="Saudável",
                mensagem="O valor recebido no mês cobre os pagamentos monitorados.",
                impacto="Menor pressão sobre caixa e capital de giro.",
                recomendacao="Continuar acompanhando inadimplência e concentração de vencimentos."
            ))

        if qtd_titulos_vencidos > 80 or valor_vencido > 300000:
            itens_fin.append(DiagnosticoItem(
                titulo="Inadimplência relevante",
                status="Crítico",
                mensagem=f"Há {int(qtd_titulos_vencidos)} títulos vencidos, somando {formatar_numero(valor_vencido, 'R$')}.",
                impacto="Compromete o caixa e aumenta risco de perdas.",
                recomendacao="Criar régua de cobrança por faixa de atraso e cliente."
            ))
        elif qtd_titulos_vencidos > 30:
            itens_fin.append(DiagnosticoItem(
                titulo="Títulos vencidos em atenção",
                status="Atenção",
                mensagem=f"Há {int(qtd_titulos_vencidos)} títulos vencidos em carteira.",
                impacto="Reduz previsibilidade de entrada de caixa.",
                recomendacao="Acompanhar aging list e priorizar maiores valores."
            ))

        status_fin = "Saudável"
        if any(i.status == "Crítico" for i in itens_fin):
            status_fin = "Crítico"
        elif any(i.status == "Atenção" for i in itens_fin):
            status_fin = "Atenção"

        diagnosticos.append(DiagnosticoSetor(
            setor="Financeiro",
            status=status_fin,
            resumo="Avalia equilíbrio de caixa, inadimplência e pressão financeira do período.",
            itens=itens_fin
        ))

        # =========================
        # DIAGNÓSTICO GERAL
        # =========================
        qtd_criticos = sum(1 for d in diagnosticos if d.status == "Crítico")
        qtd_atencao = sum(1 for d in diagnosticos if d.status == "Atenção")

        if qtd_criticos >= 2:
            status_geral = "Crítico"
            resumo_geral = "O painel indica pressão operacional e financeira relevante, com necessidade de ação gerencial prioritária."
        elif qtd_atencao >= 2:
            status_geral = "Atenção"
            resumo_geral = "O painel mostra estabilidade parcial, porém com pontos importantes que exigem acompanhamento próximo."
        else:
            status_geral = "Saudável"
            resumo_geral = "O cenário geral está equilibrado nas regras avaliadas, sem alertas severos predominantes."

        itens_gerais: list[DiagnosticoItem] = []

        if saldo_caixa_operacional < 0:
            itens_gerais.append(DiagnosticoItem(
                titulo="Capital de giro pressionado",
                status="Crítico" if saldo_caixa_operacional < -300000 else "Atenção",
                mensagem="O financeiro está pagando mais do que recebe no período.",
                impacto="Risco de aperto de caixa e dependência de capital externo.",
                recomendacao="Atuar em cobrança, prazo médio de recebimento e priorização de desembolso."
            ))

        if of_atrasadas > 20:
            itens_gerais.append(DiagnosticoItem(
                titulo="Gargalo produtivo",
                status="Crítico" if of_atrasadas > 50 else "Atenção",
                mensagem="A produção apresenta volume relevante de OFs atrasadas.",
                impacto="Pode travar faturamento, entrega e satisfação do cliente.",
                recomendacao="Criar painel de OFs por idade, motivo e responsável."
            ))

        if estoque_total > 0 and (estoque_avaria / estoque_total) * 100 > 5:
            itens_gerais.append(DiagnosticoItem(
                titulo="Qualidade do estoque exige ação",
                status="Crítico" if (estoque_avaria / estoque_total) * 100 > 10 else "Atenção",
                mensagem="Há peso relevante de estoque em situação problemática.",
                impacto="Capital parado e risco de perda de valor.",
                recomendacao="Abrir frente de saneamento e reaproveitamento do estoque."
            ))

        if not itens_gerais:
            itens_gerais.append(DiagnosticoItem(
                titulo="Ambiente controlado",
                status="Saudável",
                mensagem="Os principais pilares analisados estão dentro de uma faixa administrável.",
                impacto="Maior previsibilidade operacional e financeira.",
                recomendacao="Continuar refinando metas e alertas automáticos."
            ))

        geral = DiagnosticoSetor(
            setor="Geral",
            status=status_geral,
            resumo=resumo_geral,
            itens=itens_gerais
        )

        return diagnosticos, geral
    # =========================================================
    # STATUS DE CARREGAMENTO
    # =========================================================
    inicio_execucao = time.perf_counter()
    render_status_topo("Iniciando carregamento do painel...", 0.0, False)

    def atualizar_loading(etapa: str, atual: int, total: int):
        tempo_decorrido = time.perf_counter() - inicio_execucao
        percentual = min(int((atual / total) * 100), 100)
        render_status_topo(f"{etapa} ({percentual}%)", tempo_decorrido, False)
    # =========================================================
    # KPIs
    # =========================================================
    total_etapas = 22
    etapa = 0
    etapas_kpi = [
        ("Carregando faturamento...", faturamento.get_kpi),
        ("Carregando pedidos...", pedidos.get_kpi),
        ("Carregando financeiro...", financeiro.get_kpi),
        ("Carregando estoque...", estoque.get_kpi),
        ("Carregando compras pendentes...", compras_pendentes.get_kpi),
        ("Carregando pedidos do mês...", pedidos_mes.get_kpi),
        ("Calculando prazo médio de entrega...", pedidos_mes.get_kpi_prazo_medio_entrega),
        ("Carregando OF dispersão...", OF_dispersao.get_kpi),
        ("Carregando CQ liberação...", cq_liberacao.get_kpi),
        ("Carregando produção...", ordem_fabric.get_kpi),
        ("Carregando OFs atrasadas...", ordem_fabric.get_kpi_of_atrasadas),
        ("Carregando correções...", correcoes.get_kpi),
        ("Carregando OFs abertas 997...", ordem_fabric.get_kpi_of_abertas_997),
        ("Carregando margem...", margem.get_kpi),
        ("Carregando contas a receber...", areceber.get_kpi),
        ("Carregando avarias de estoque...", estoque.get_kpi_avarias),
        ("Carregando entradas...", entradas.get_kpi),
        ("Carregando itens críticos...", itemcritico.get_kpi),
        ("Carregando estrutura...", estrutura.get_kpi),
        ("Carregando reposição x médio...", reposicaoxmedio.get_kpi),
        ("Carregando metas...", meta.get_kpi),
        ("Carregando meta atingida...", metaatingida.get_kpi),
    ]

    total_etapas = len(etapas_kpi)
    kpi_faturamento = faturamento.get_kpi()
    etapa += 1
    atualizar_loading("Carregando faturamento...", etapa, total_etapas)

    kpi_pedidos = pedidos.get_kpi()
    etapa += 1
    atualizar_loading("Carregando pedidos...", etapa, total_etapas)

    kpi_financeiro = financeiro.get_kpi()
    etapa += 1
    atualizar_loading("Carregando financeiro...", etapa, total_etapas)

    kpi_estoque = estoque.get_kpi()
    etapa += 1
    atualizar_loading("Carregando estoque...", etapa, total_etapas)

    kpi_compras_pendentes = compras_pendentes.get_kpi()
    etapa += 1
    atualizar_loading("Carregando compras pendentes...", etapa, total_etapas)

    kpi_pedidos_mes = pedidos_mes.get_kpi()
    etapa += 1
    atualizar_loading("Carregando pedidos do mês...", etapa, total_etapas)

    kpi_prazo_entrega = pedidos_mes.get_kpi_prazo_medio_entrega()
    etapa += 1
    atualizar_loading("Calculando prazo médio de entrega...", etapa, total_etapas)

    kpi_of_dispersao = OF_dispersao.get_kpi()
    etapa += 1
    atualizar_loading("Carregando OF dispersão...", etapa, total_etapas)

    kpi_cq_liberacao = cq_liberacao.get_kpi()
    etapa += 1
    atualizar_loading("Carregando CQ liberação...", etapa, total_etapas)

    kpi_producao = ordem_fabric.get_kpi()
    etapa += 1
    atualizar_loading("Carregando produção...", etapa, total_etapas)

    kpi_of_atrasadas = ordem_fabric.get_kpi_of_atrasadas()
    etapa += 1
    atualizar_loading("Carregando OFs atrasadas...", etapa, total_etapas)

    kpi_correcoes = correcoes.get_kpi()
    etapa += 1
    atualizar_loading("Carregando correções...", etapa, total_etapas)

    kpi_of_abertas_997 = ordem_fabric.get_kpi_of_abertas_997()
    etapa += 1
    atualizar_loading("Carregando OFs abertas 997...", etapa, total_etapas)

    kpi_margem = margem.get_kpi()
    etapa += 1
    atualizar_loading("Carregando margem...", etapa, total_etapas)

    kpi_areceber = areceber.get_kpi()
    etapa += 1
    atualizar_loading("Carregando contas a receber...", etapa, total_etapas)

    kpi_estoque_avaria = estoque.get_kpi_avarias()
    etapa += 1
    atualizar_loading("Carregando avarias de estoque...", etapa, total_etapas)

    kpi_entradas = entradas.get_kpi()
    etapa += 1
    atualizar_loading("Carregando entradas...", etapa, total_etapas)

    kpi_itemcritico = itemcritico.get_kpi()
    etapa += 1
    atualizar_loading("Carregando itens críticos...", etapa, total_etapas)

    kpi_estrutura = estrutura.get_kpi()
    etapa += 1
    atualizar_loading("Carregando estrutura...", etapa, total_etapas)

    kpi_reposicao = reposicaoxmedio.get_kpi()
    etapa += 1
    atualizar_loading("Carregando reposição x médio...", etapa, total_etapas)

    kpi_meta = meta.get_kpi()
    etapa += 1
    atualizar_loading("Carregando metas...", etapa, total_etapas)

    kpi_metaatingida = metaatingida.get_kpi()
    etapa += 1
    atualizar_loading("Carregando meta atingida...", etapa, total_etapas)
    # =========================================================
    # ORGANIZAÇÃO POR SETOR
    # =========================================================
    setores = {
        "Comercial": [
            AreaIndicador(
            nome=kpi_metaatingida["nome"],
            valor=kpi_metaatingida["valor"],
            valor_anterior=kpi_metaatingida["valor_anterior"],
            unidade=kpi_metaatingida["unidade"],
            cor=kpi_metaatingida["cor"],
            extra=kpi_metaatingida["extra"]
        ),
            AreaIndicador(
                nome=kpi_faturamento["nome"],
                valor=kpi_faturamento["valor"],
                valor_anterior=kpi_faturamento["valor_anterior"],
                unidade=kpi_faturamento["unidade"],
                cor=kpi_faturamento["cor"],
                extra=kpi_faturamento.get("extra")
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
            AreaIndicador(
                nome=kpi_meta["nome"],
                valor=kpi_meta["valor"],
                valor_anterior=kpi_meta["valor_anterior"],
                unidade=kpi_meta["unidade"],
                cor=kpi_meta["cor"],
                extra=kpi_meta["extra"]
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
            AreaIndicador(
                nome=kpi_estrutura["nome"],
                valor=kpi_estrutura["valor"],
                valor_anterior=kpi_estrutura["valor_anterior"],
                unidade=kpi_estrutura["unidade"],
                cor=kpi_estrutura["cor"],
                extra=kpi_estrutura["extra"]
            )
        ],

        "Suprimentos": [
            AreaIndicador(**kpi_estoque),
            AreaIndicador(**kpi_estoque_avaria),
            AreaIndicador(
                nome=kpi_itemcritico["nome"],
                valor=kpi_itemcritico["valor"],
                valor_anterior=kpi_itemcritico["valor_anterior"],
                unidade=kpi_itemcritico["unidade"],
                cor=kpi_itemcritico["cor"],
                extra=kpi_itemcritico["extra"]
            ),
            AreaIndicador(
                nome=kpi_compras_pendentes["nome"],
                valor=kpi_compras_pendentes["valor"],
                valor_anterior=kpi_compras_pendentes["valor_anterior"],
                unidade=kpi_compras_pendentes["unidade"],
                cor=kpi_compras_pendentes["cor"],
                extra=kpi_compras_pendentes.get("extra")
            ),
            AreaIndicador(
                nome=kpi_entradas["nome"],
                valor=kpi_entradas["valor"],
                valor_anterior=kpi_entradas["valor_anterior"],
                unidade=kpi_entradas["unidade"],
                cor=kpi_entradas["cor"],
                extra=kpi_entradas.get("extra")
            ),

            AreaIndicador(
                nome=kpi_reposicao["nome"],
                valor=kpi_reposicao["valor"],
                valor_anterior=kpi_reposicao["valor_anterior"],
                unidade=kpi_reposicao["unidade"],
                cor=kpi_reposicao["cor"],
                extra=kpi_reposicao["extra"]
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
                    f'Venc.: {formatar_numero(kpi_financeiro.get("total_vencido", 0), "R$")}<br>'
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
    tempo_total = time.perf_counter() - inicio_execucao
    render_status_topo("Painel carregado com sucesso.", tempo_total, True)
    st.session_state["loading_message"] = "Painel carregado com sucesso."
    st.session_state["loading_elapsed"] = tempo_total
    st.session_state["loading_done"] = True
    # =========================================================
    # BASES AUXILIARES
    # =========================================================
    todas_areas = [area for lista in setores.values() for area in lista]
    df_entradas_mes = entradas.get_entradas_mes_df()

    diagnosticos_setores, diagnostico_geral = gerar_diagnosticos(
        kpi_faturamento=kpi_faturamento,
        kpi_pedidos=kpi_pedidos,
        kpi_financeiro=kpi_financeiro,
        kpi_estoque=kpi_estoque,
        kpi_compras_pendentes=kpi_compras_pendentes,
        kpi_prazo_entrega=kpi_prazo_entrega,
        kpi_of_dispersao=kpi_of_dispersao,
        kpi_cq_liberacao=kpi_cq_liberacao,
        kpi_producao=kpi_producao,
        kpi_of_atrasadas=kpi_of_atrasadas,
        kpi_correcoes=kpi_correcoes,
        kpi_of_abertas_997=kpi_of_abertas_997,
        kpi_margem=kpi_margem,
        kpi_areceber=kpi_areceber,
        kpi_estoque_avaria=kpi_estoque_avaria,
        kpi_entradas=kpi_entradas,
        #kpi_itemcritico = kpi_itemcritico,
        
    )

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
    # SIDEBAR
    # =========================================================
    st.sidebar.title("Auditi")
    st.sidebar.caption("Painel executivo por setor")

    # =========================================================
    # CABEÇALHO
    # =========================================================
    #st.title("Auditi | Painel de Indicadores")


    # # =========================================================
    # # DIAGNÓSTICO GERAL
    # # =========================================================
    # st.markdown('<div class="section-title">Diagnóstico automático</div>', unsafe_allow_html=True)
    # with st.expander("Diagnóstico Automático", expanded=False):
    #     render_diagnostico_box(diagnostico_geral)

    # with st.expander("Ver diagnóstico por departamento", expanded=False):
    #     col_d1, col_d2 = st.columns(2)

    #     metade = (len(diagnosticos_setores) + 1) // 2
    #     esquerda = diagnosticos_setores[:metade]
    #     direita = diagnosticos_setores[metade:]

    #     with col_d1:
    #         for diag in esquerda:
    #             render_diagnostico_box(diag)

    #     with col_d2:
    #         for diag in direita:
    #             render_diagnostico_box(diag)

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
    # RESUMO EXECUTIVO NA SIDEBAR
    # =========================================================

    st.sidebar.markdown("### 📊 Resumo Executivo")

    # Setores monitorados
    st.sidebar.markdown(
        f"""
        <div class="metric-card card-green">
            <div class="metric-title">Setores monitorados</div>
            <div class="metric-value">{len(setores)}</div>
            <div class="metric-delta">Painel ativo</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Indicadores ativos
    st.sidebar.markdown(
        f"""
        <div class="metric-card card-yellow">
            <div class="metric-title">Indicadores ativos</div>
            <div class="metric-value">{len(todas_areas)}</div>
            <div class="metric-delta">Cards carregados</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Consultas executadas
    st.sidebar.markdown(
        f"""
        <div class="metric-card card-blue">
            <div class="metric-title">Consultas executadas</div>
            <div class="metric-value">{len(todas_areas)}</div>
            <div class="metric-delta">Módulos carregados</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Eficiência de carga
    eficiencia = 100 if all(a.valor >= 0 for a in todas_areas) else 0

    st.sidebar.markdown(
        f"""
        <div class="metric-card card-pink">
            <div class="metric-title">Eficiência de carga</div>
            <div class="metric-value">{eficiencia:.1f}%</div>
            <div class="metric-delta">Base integrada</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================
    # GRÁFICO DE SETORES
    # =========================================================

    df_setores = pd.DataFrame(
        [
            {"Setor": setor, "Qtd Indicadores": len(indicadores)}
            for setor, indicadores in setores.items()
        ]
    )

    st.sidebar.plotly_chart(
        px.bar(
            df_setores,
            x="Setor",
            y="Qtd Indicadores",
            text_auto=True,
            title="Indicadores por setor"
        ),
        use_container_width=True,
    )
    ###############################################################################################################

    df_meta_grafico = meta.get_meta_vendedor_grafico()

    if not df_meta_grafico.empty:
        fig_meta = px.bar(
            df_meta_grafico,
            x="label",
            y="valor",
            color="periodo",
            barmode="group",
            text="valor",
            title="Faturamento por Vendedor - Mês Atual x Mês Anterior",
            hover_data=["vendedor", "filial"]
        )

        fig_meta.update_traces(
            texttemplate="R$ %{y:,.2f}",
            textposition="outside",
            textangle=-90,
            textfont=dict(size=15),
            cliponaxis=False
        )

        fig_meta.update_layout(
            uniformtext_minsize=15,
            uniformtext_mode="show",
            height=750
        )

        fig_meta.update_layout(
            title_font=dict(size=20),
            xaxis_title="Vendedor / Filial",
            yaxis_title="Valor Faturado",
            xaxis=dict(
                tickangle=-45,
                tickfont=dict(size=12),
                title_font=dict(size=14)
            ),
            yaxis=dict(
                tickfont=dict(size=12),
                title_font=dict(size=14)
            ),
            legend=dict(
                font=dict(size=12)
            ),
            height=650
        )

        st.plotly_chart(fig_meta, use_container_width=True)
    else:
        st.info("Sem dados de faturamento por vendedor para o período.")
    ####################################################################################################################
    # Grafico Meta x Realizado por mês
  

    df_meta_matriz = metaatingida.get_tabela_meta_matriz()

    if not df_meta_matriz.empty:
        st.markdown("### Meta x Realizado ao Longo do Ano")
        st.dataframe(
            metaatingida.formatar_tabela_meta_matriz(df_meta_matriz),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Sem dados de metas para o ano atual.")

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
                    "Variação %": (
                    f"{area.delta_perc:.2f}%".replace(".", ",")
                    if area.delta_perc is not None
                    else ""
                ),
                }
            )

    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)



