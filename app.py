import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação & Expansão", layout="wide")

st.title("Projeção de Maturação e Análise de Performance")
st.markdown("---")

# Funções Utilitárias de Limpeza
def clean_numeric(val):
    """Converte valores variados (strings com vírgula, R$, etc) em float."""
    if pd.isna(val) or val == "" or val == "-":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        s = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(s)
    except:
        return 0.0

# 2. ENTRADA DE DADOS DE PROJEÇÃO
st.sidebar.header("1. Dados de Projeção")
arquivo_subido = st.sidebar.file_uploader(
    "Upload da planilha de Taxas de Crescimento:", 
    type=["xlsx", "xls", "csv"],
    key="proj_file"
)

taxas = []

if arquivo_subido is not None:
    try:
        if "csv" in arquivo_subido.name.lower():
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)

        df_growth = df_growth.dropna(axis=1, how='all')

        st.sidebar.header("Configurações da Projeção")
        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Estudo 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        estados_alvo = ["RS", "SC", "PR"]
        colunas_disponiveis = [c for c in df_growth.columns if any(est in str(c) for est in estados_alvo)]
        
        if colunas_disponiveis:
            estado_sel = st.sidebar.selectbox("Estado para análise:", estados_alvo)
            cols_matching = [c for c in df_growth.columns if estado_sel in str(c)]
            col_nome_real = cols_matching[-1] 
            taxas = pd.to_numeric(df_growth[col_nome_real], errors='coerce').fillna(0).values

            projecao = []
            percentual_inicial = 0.77 if estado_sel == "RS" else 0.60
            valor_atual = valor_estudo * percentual_inicial
            projecao.append(valor_atual)
            
            for i in range(1, 36):
                if i < len(taxas):
                    taxa_mes = taxas[i]
                    valor_atual = valor_atual * (1 + taxa_mes)
                    projecao.append(valor_atual)
            
            df_res = pd.DataFrame({
                "Mês": range(1, len(projecao) + 1),
                "Faturamento": projecao
            })
            df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100
            meses_grafico = [1, 3, 6, 9, 12, 18, 24, 30, 36]

            c1, c2 = st.columns([2, 1])
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                             title=f"Evolução de Faturamento Projetada - {estado_sel}",
                             template="plotly_white", color_discrete_sequence=["#00CC96"])
                fig.update_layout(xaxis=dict(tickmode='array', tickvals=meses_grafico), yaxis_tickformat="R$,.2f")
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                fig.add_vline(x=12, line_dash="dot", line_color="orange", 
                             annotation_text="Corte 12 Meses", annotation_position="top left")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("Marcos de Maturação")
                st.dataframe(df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                            height=450, use_container_width=True, hide_index=True)

            st.markdown("---")
            m1, m12, m2, m3 = st.columns(4)
            m1.metric("Venda Inicial (Mês 1)", f"R$ {projecao[0]:,.2f}", delta=f"{int(percentual_inicial*100)}% do Alvo")
            
            v_12 = projecao[11] if len(projecao) >= 12 else 0
            perc_12 = (v_12 / valor_estudo) * 100 if valor_estudo > 0 else 0
            m12.metric("Venda 12 Meses", f"R$ {v_12:,.2f}", delta=f"{perc_12:.2f}% do Alvo")
            
            v_final = projecao[-1]
            perc_final = (v_final / valor_estudo) * 100 if valor_estudo > 0 else 0
            m2.metric("Venda Final (Mês 36)", f"R$ {v_final:,.2f}", delta=f"{perc_final:.2f}% do Alvo")
            
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Acima de 36m"
            m3.metric("Maturação (100%)", f"Mês {mes_mat}")

    except Exception as e:
        st.error(f"Erro na Projeção: {e}")

# --- SEÇÃO: HISTÓRICO REAL ---
st.markdown("### Histórico Real vs Crescimento Projetado")
st.sidebar.markdown("---")
st.sidebar.header("2. Dados Históricos")
arquivo_historico = st.sidebar.file_uploader(
    "Upload da planilha de Vendas Realizadas (12 Meses):", 
    type=["xlsx", "xls", "csv"],
    key="hist_file"
)

if arquivo_historico is not None:
    try:
        if "csv" in arquivo_historico.name.lower():
            df_hist = pd.read_csv(arquivo_historico, decimal='.', engine='python')
        else:
            df_hist = pd.read_excel(arquivo_historico)

        if 'Desc_Filial' in df_hist.columns:
            filiais = sorted(df_hist['Desc_Filial'].unique())
            filial_sel = st.selectbox("Unidade para análise de histórico:", filiais)
            
            df_loja = df_hist[df_hist['Desc_Filial'] == filial_sel].copy()
            df_loja = df_loja.sort_values(by='AnoMes')

            venda_inicial_real = df_loja['Mercadoria'].iloc[0]
            esperado = [venda_inicial_real]
            
            for i in range(1, len(df_loja)):
                if len(taxas) > i:
                    proximo_valor = esperado[-1] * (1 + taxas[i])
                    esperado.append(proximo_valor)
                else:
                    esperado.append(esperado[-1])
            
            df_loja['Crescimento_Esperado'] = esperado

            meses_map = {
                '01': 'Jan', '02': 'Fev', '03': 'Mar', '04': 'Abr',
                '05': 'Mai', '06': 'Jun', '07': 'Jul', '08': 'Ago',
                '09': 'Set', '10': 'Out', '11': 'Nov', '12': 'Dez'
            }
            
            def formatar_mes_pt(anomes):
                try:
                    s_anomes = str(anomes)
                    if '-' in s_anomes:
                        ano, mes = s_anomes.split('-')
                    else:
                        ano, mes = s_anomes[:4], s_anomes[4:]
                    return f"{meses_map[mes]}/{ano[2:]}"
                except: return str(anomes)

            df_loja['Mes_PT'] = df_loja['AnoMes'].apply(formatar_mes_pt)
            df_loja['Valor_Texto'] = df_loja['Mercadoria'].apply(
                lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            )

            fig_hist = px.bar(df_loja, x='Mes_PT', y='Mercadoria', 
                             title=f"Histórico Real vs Projeção ({filial_sel})",
                             labels={'Mercadoria': 'Faturamento Real', 'Mes_PT': 'Período'},
                             template="plotly_white",
                             text='Valor_Texto') 

            fig_hist.add_scatter(x=df_loja['Mes_PT'], y=df_loja['Crescimento_Esperado'], 
                                 mode='lines+markers', 
                                 name='Projeção Base Estado',
                                 line=dict(color='orange', width=3))
            
            fig_hist.update_traces(marker_color='#3366CC', textposition='outside', selector=dict(type='bar'))
            fig_hist.update_layout(yaxis_tickformat="R$,.2f", xaxis_title=None, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_hist, use_container_width=True)
            
    except Exception as e:
        st.error(f"Erro no processamento do histórico: {e}")


# --- SEÇÃO: ANÁLISE DE LOJAS NEGATIVAS ---
st.markdown("---")
st.header("Análise de Lojas com Resultado Negativo (Expansão)")

st.sidebar.markdown("---")
st.sidebar.header("3. Análise de Negativas")
arquivo_negativas = st.sidebar.file_uploader(
    "Upload da planilha de Lojas Negativas:", 
    type=["xlsx", "xls", "csv"],
    key="neg_file"
)

if arquivo_negativas is not None:
    try:
        if "csv" in arquivo_negativas.name.lower():
            df_neg = pd.read_csv(arquivo_negativas, decimal=',', engine='python')
        else:
            df_neg = pd.read_excel(arquivo_negativas)

        # Limpeza e conversão forçada para numérico para evitar erros de gradiente
        df_neg = df_neg.dropna(subset=['Cod Unidade', 'RO Acum'])
        df_neg['RO Acum'] = df_neg['RO Acum'].apply(clean_numeric)
        df_neg['%Aluguel Mês'] = df_neg['%Aluguel Mês'].apply(clean_numeric)
        df_neg['%RO Mês'] = df_neg['%RO Mês'].apply(clean_numeric)

        total_prejuizo_acum = df_neg['RO Acum'].sum()
        media_aluguel_perc = df_neg['%Aluguel Mês'].mean() * 100
        total_lojas = len(df_neg)

        c1, c2, c3 = st.columns(3)
        c1.metric("Prejuízo Acumulado Total", f"R$ {total_prejuizo_acum:,.2f}", delta_color="inverse")
        c2.metric("Qtd. Lojas Analisadas", f"{total_lojas} unidades")
        c3.metric("Peso Médio Aluguel", f"{media_aluguel_perc:.2f}%")

        st.subheader("Diagnóstico de Ofensores e Padrões")
        t1, t2, t3 = st.tabs(["🔥 Top Ofensores", "🏠 Custo de Ocupação", "🏢 Perfil de Loja"])

        with t1:
            df_neg_sorted = df_neg.sort_values(by='RO Acum', ascending=True).head(12)
            fig_ofensores = px.bar(df_neg_sorted, x='Desc_CC', y='RO Acum', 
                                  title="Unidades com Maior Prejuízo Acumulado",
                                  color='RO Acum', color_continuous_scale='Reds_r')
            st.plotly_chart(fig_ofensores, use_container_width=True)

        with t2:
            fig_corr = px.scatter(df_neg, x='%Aluguel Mês', y='%RO Mês', size='Aluguel Mês', 
                                 hover_name='Desc_CC', color='Diretor', title="Peso do Aluguel vs Margem Operacional (%)")
            st.plotly_chart(fig_corr, use_container_width=True)

        with t3:
            df_pos = df_neg.groupby('Posição Loja')['RO Acum'].mean().reset_index()
            fig_pos = px.pie(df_pos, values=df_pos['RO Acum'].abs(), names='Posição Loja', title="Prejuízo Médio por Posição")
            st.plotly_chart(fig_pos, use_container_width=True)

        # Uso seguro de gradiente (somente colunas garantidas como numéricas)
        st.dataframe(df_neg.style.background_gradient(subset=['RO Acum'], cmap='Reds_r'), use_container_width=True)

    except Exception as e:
        st.error(f"Erro no processamento das Lojas Negativas: {e}")


# --- SEÇÃO DRE ---
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")

st.sidebar.markdown("---")
st.sidebar.header("4. Dados Financeiros (DRE)")
arquivo_dre = st.sidebar.file_uploader(
    "Upload da planilha de DRE:", 
    type=["xlsx", "xls", "csv"],
    key="dre_file"
)

if arquivo_dre is not None:
    try:
        df_dre_raw = pd.read_excel(arquivo_dre, header=None)
        
        termos = {
            "RB": "Receita Bruta", "RL": "Receita Líquida", "MC": "Margem de Contribuição",
            "PVL": "Perdas Vencidos Liquido", "DISC": "Discrepância _ Estoque",
            "FOLHA": "Despesas Folha", "ADM": "Despesas ADM", "OPER": "Despesas Operação",
            "RES": "Resultado Operacional"
        }

        indices = {}
        for chave, texto in termos.items():
            match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains(texto, case=False, na=False)]
            if not match.empty:
                indices[chave] = match.index[0]

        def pegar_v(chave):
            if chave in indices:
                val = df_dre_raw.iloc[indices[chave], 3] 
                return clean_numeric(val)
            return 0.0

        vals = {k: pegar_v(k) for k in termos.keys()}
        receita_base = vals['RL'] if vals['RL'] > 0 else vals['RB']

        # Métricas de topo
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receita Líquida", f"R$ {vals['RL']:,.2f}")
        c2.metric("Margem Contrib.", f"R$ {vals['MC']:,.2f}")
        c3.metric("Resultado Oper.", f"R$ {vals['RES']:,.2f}", delta_color="normal" if vals['RES']>=0 else "inverse")
        c4.metric("Perdas Totais", f"R$ {abs(vals['PVL'])+abs(vals['DISC']):,.2f}")

        st.markdown("---")
        st.subheader("Tabela de Dados Financeiros Detalhada")
        
        df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")
        
        # Identificação dinâmica de colunas para evitar o erro de 'Index Out of Range'
        col_indices = []
        for i, col in enumerate(df_exibicao.columns):
            header_sample = df_exibicao.iloc[0:5, i].astype(str).str.upper().to_list()
            if any("REALIZADO" in s for s in header_sample):
                col_indices.append(df_exibicao.columns[i])

        # Estilização Segura
        def formatador_decimal_safe(val):
            try:
                num = clean_numeric(val)
                return f"{num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            except: return val

        # Aplicando apenas formatação básica sem gradientes complexos no DRE (causadores de erro em células mescladas)
        st.dataframe(df_exibicao.astype(str), use_container_width=True)

    except Exception as e:
        st.error(f"Erro no DRE: {e}")
