import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("Projeção de Maturação: Analisador de Dados")
st.markdown("---")

# 2. ENTRADA DE DADOS DE PROJEÇÃO
st.sidebar.header("Dados de Projeção")
arquivo_subido = st.sidebar.file_uploader(
    "Upload da planilha de Taxas de Crescimento:", 
    type=["xlsx", "xls", "csv"],
    key="proj_file"
)

# Inicializa variável de taxas para evitar erro de escopo
taxas = []

if arquivo_subido is not None:
    try:
        if "csv" in arquivo_subido.name.lower():
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)

        df_growth = df_growth.dropna(axis=1, how='all')

        # --- PARÂMETROS ---
        st.sidebar.header("Configurações da Projeção")
        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Estudo 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        # Filtragem por estado
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

            # --- DASHBOARD DE PROJEÇÃO ---
            c1, c2 = st.columns([2, 1])
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                             title=f"Evolução de Faturamento Projetada - {estado_sel}",
                             template="plotly_white", color_discrete_sequence=["#00CC96"])
                fig.update_layout(xaxis=dict(tickmode='array', tickvals=meses_grafico), yaxis_tickformat="R$,.2f")
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
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
            m12.metric("Venda 12 Meses", f"R$ {v_12:,.2f}", delta=f"{perc_12:.1f}% do Alvo")
            
            v_final = projecao[-1]
            perc_final = (v_final / valor_estudo) * 100 if valor_estudo > 0 else 0
            m2.metric("Venda Final (Mês 36)", f"R$ {v_final:,.2f}", delta=f"{perc_final:.1f}% do Alvo")
            
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Acima de 36m"
            m3.metric("Maturação (100%)", f"Mês {mes_mat}")

    except Exception as e:
        st.error(f"Erro na Projeção: {e}")

# --- SEÇÃO: HISTÓRICO REAL ---
st.markdown("### Histórico Real vs Crescimento Projetado")
st.sidebar.markdown("---")
st.sidebar.header("Dados Históricos")
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

# --- SEÇÃO DRE ---
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")

st.sidebar.markdown("---")
st.sidebar.header("Dados Financeiros (DRE)")
arquivo_dre = st.sidebar.file_uploader(
    "Upload da planilha de DRE:", 
    type=["xlsx", "xls", "csv"],
    key="dre_file"
)

if arquivo_dre is not None:
    try:
        df_dre_raw = pd.read_excel(arquivo_dre, header=None)
        
        termos = {
            "RB": "Receita Bruta",
            "MC": "Margem de Contribuição",
            "PVL": "Perdas Vencidos Liquido",
            "DISC": "Discrepância _ Estoque",
            "FOLHA": "Despesas Folha",
            "ADM": "Despesas ADM",
            "OPER": "Despesas Operação",
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
                return pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0.0
            return 0.0

        vals = {k: pegar_v(k) for k in termos.keys()}

        # 1. INDICADORES PRINCIPAIS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {vals['RB']:,.2f}")
        c2.metric("Margem de Contribuição", f"R$ {vals['MC']:,.2f}")
        
        res_cor = "normal" if vals['RES'] >= 0 else "inverse"
        c3.metric("Resultado Operacional", f"R$ {vals['RES']:,.2f}", delta_color=res_cor)
        
        perdas_totais = abs(vals['PVL']) + abs(vals['DISC'])
        c4.metric("Perdas e Discrepâncias", f"R$ {perdas_totais:,.2f}")

        # 2. DIAGNÓSTICO
        st.subheader("Análise de Performance Operacional")
        col_diag, col_graf = st.columns([1, 1])
        
        with col_diag:
            st.write("Alertas de Indicadores:")
            if vals['RES'] < 0:
                st.error(f"Resultado Negativo: Déficit operacional de R$ {abs(vals['RES']):,.2f}.")
            
            perc_margem = (vals['MC'] / vals['RB'] * 100) if vals['RB'] > 0 else 0
            if perc_margem < 30:
                st.warning(f"Margem Abaixo da Meta ({perc_margem:.1f}%): Referência de mercado é 30%.")
            
            perc_perda = (perdas_totais / vals['RB'] * 100) if vals['RB'] > 0 else 0
            if perc_perda > 1.5:
                st.warning(f"Nível de Quebra Elevado ({perc_perda:.2f}%): Acima do limite de 1.5%.")

            perc_folha = (abs(vals['FOLHA']) / vals['RB'] * 100) if vals['RB'] > 0 else 0
            if perc_folha > 12:
                st.info(f"Indicador de Folha: {perc_folha:.1f}% do faturamento.")

        with col_graf:
            df_gastos = pd.DataFrame({
                "Conta": ["Folha", "ADM", "Operação", "Quebra/Perdas"],
                "Valor": [abs(vals['FOLHA']), abs(vals['ADM']), abs(vals['OPER']), perdas_totais]
            }).sort_values(by="Valor", ascending=False)
            
            fig_ofensores = px.pie(df_gastos, values='Valor', names='Conta', 
                                   title="Composição de Gastos Operacionais",
                                   color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_ofensores, use_container_width=True)

        # --- TABELA DE DADOS FINANCEIROS DETALHADA COM FORMATAÇÃO DINÂMICA ---
        st.markdown("---")
        st.subheader("Tabela de Dados Financeiros Detalhada")
        
        # Limpeza inicial
        df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")

        # Identificação dinâmica das colunas "AV-RI" e "Realizado"
        colunas_avri = []
        colunas_realizado = []
        
        for col_idx in range(len(df_exibicao.columns)):
            # Procura AV-RI no cabeçalho (3 primeiras linhas)
            if df_exibicao.iloc[0:3, col_idx].astype(str).str.contains("AV-RI").any():
                colunas_avri.append(df_exibicao.columns[col_idx])
            # Procura Realizado no cabeçalho (3 primeiras linhas)
            if df_exibicao.iloc[0:3, col_idx].astype(str).str.contains("Realizado").any():
                colunas_realizado.append(df_exibicao.columns[col_idx])

        # Funções de formatação
        def formatador_porcentagem(val):
            try:
                if val == "" or val == "-": return val
                num = pd.to_numeric(val, errors='coerce')
                if pd.notnull(num) and not isinstance(val, str):
                    return f"{num * 100:.2f}%".replace('.', ',')
                return val
            except: return val

        def formatador_inteiro(val):
            try:
                if val == "" or val == "-": return val
                num = pd.to_numeric(val, errors='coerce')
                if pd.notnull(num) and not isinstance(val, str):
                    # Formata como inteiro com separador de milhar (ponto)
                    return f"{int(round(num)):,}".replace(',', '.')
                return val
            except: return val

        # Aplicação dos estilos
        colunas_pct = list(set([2] + colunas_avri)) # Coluna 2 (%Meta) + colunas AV-RI
        
        st.dataframe(
            df_exibicao.style.format(subset=colunas_pct, formatter=formatador_porcentagem)
                             .format(subset=colunas_realizado, formatter=formatador_inteiro), 
            use_container_width=True, 
            hide_index=True
        )

    except Exception as e:
        st.error(f"Erro no processamento do DRE: {e}")
