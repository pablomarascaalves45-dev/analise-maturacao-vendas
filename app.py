import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DO DASHBOARD
st.set_page_config(page_title="Gestão de Maturação e DRE", layout="wide")

st.title("Sistema de Análise: Expansão e Performance")
st.markdown("---")

def clean_numeric(val):
    if pd.isna(val) or val == "" or val == "-" or val == " ":
        return 0.0
    try:
        s = str(val).replace('R$', '').replace('%', '').strip()
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except:
        return 0.0

# 2. PROJEÇÃO DE CRESCIMENTO
st.sidebar.header("1. Parâmetros de Projeção")
arquivo_subido = st.sidebar.file_uploader(
    "Taxas de Crescimento:", 
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

        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Meta 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        estados_alvo = ["RS", "SC", "PR"]
        estado_sel = st.sidebar.selectbox("Estado Base:", estados_alvo)
        
        cols_matching = [c for c in df_growth.columns if estado_sel in str(c)]
        if cols_matching:
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
                             title=f"Curva de Maturação Esperada - {estado_sel}",
                             template="plotly_white", color_discrete_sequence=["#00CC96"])
                fig.update_layout(xaxis=dict(tickmode='array', tickvals=meses_grafico), yaxis_tickformat="R$,.2f")
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("Tabela de Evolução")
                st.dataframe(df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                            height=400, use_container_width=True, hide_index=True)

            m1, m12, m2, m3 = st.columns(4)
            m1.metric("Mês 01", f"R$ {projecao[0]:,.2f}", delta=f"{int(percentual_inicial*100)}% da Meta")
            v_12 = projecao[11] if len(projecao) >= 12 else 0
            perc_12 = (v_12 / valor_estudo) * 100 if valor_estudo > 0 else 0
            m12.metric("Mês 12", f"R$ {v_12:,.2f}", delta=f"{perc_12:.2f}% da Meta")
            v_final = projecao[-1]
            perc_final = (v_final / valor_estudo) * 100 if valor_estudo > 0 else 0
            m2.metric("Mês 36", f"R$ {v_final:,.2f}", delta=f"{perc_final:.2f}% da Meta")
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "N/A"
            m3.metric("Tempo para 100%", f"{mes_mat} Meses")

    except Exception as e:
        st.error(f"Erro no processamento da projeção: {e}")

# 3. COMPARATIVO REAL
st.markdown("---")
st.sidebar.header("2. Dados Históricos")
arquivo_historico = st.sidebar.file_uploader(
    "Histórico de Vendas Realizadas:", 
    type=["xlsx", "xls", "csv"], 
    key="hist_file"
)

if arquivo_historico is not None:
    try:
        df_hist = pd.read_csv(arquivo_historico, decimal='.', engine='python') if "csv" in arquivo_historico.name.lower() else pd.read_excel(arquivo_historico)

        if 'Desc_Filial' in df_hist.columns:
            filiais = sorted(df_hist['Desc_Filial'].unique())
            filial_sel = st.selectbox("Filial para comparação:", filiais)
            df_loja = df_hist[df_hist['Desc_Filial'] == filial_sel].copy().sort_values(by='AnoMes')
            
            venda_inicial_real = df_loja['Mercadoria'].iloc[0]
            esperado = [venda_inicial_real]
            for i in range(1, len(df_loja)):
                if len(taxas) > i:
                    esperado.append(esperado[-1] * (1 + taxas[i]))
                else:
                    esperado.append(esperado[-1])
            
            df_loja['Crescimento_Esperado'] = esperado
            meses_map = {'01':'Jan','02':'Fev','03':'Mar','04':'Abr','05':'Mai','06':'Jun','07':'Jul','08':'Ago','09':'Set','10':'Out','11':'Nov','12':'Dez'}
            
            def formatar_mes_pt(anomes):
                try:
                    s_anomes = str(anomes)
                    ano, mes = (s_anomes.split('-') if '-' in s_anomes else (s_anomes[:4], s_anomes[4:]))
                    return f"{meses_map[mes]}/{ano[2:]}"
                except: return str(anomes)

            df_loja['Mes_PT'] = df_loja['AnoMes'].apply(formatar_mes_pt)
            df_loja['Valor_Texto'] = df_loja['Mercadoria'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            
            fig_hist = px.bar(df_loja, x='Mes_PT', y='Mercadoria', title=f"Realizado vs Projetado: {filial_sel}", template="plotly_white", text='Valor_Texto') 
            fig_hist.add_scatter(x=df_loja['Mes_PT'], y=df_loja['Crescimento_Esperado'], mode='lines+markers', name='Projeção Teórica', line=dict(color='orange', width=3))
            fig_hist.update_traces(marker_color='#3366CC', textposition='outside', selector=dict(type='bar'))
            st.plotly_chart(fig_hist, use_container_width=True)
    except Exception as e:
        st.error(f"Erro no histórico: {e}")


# ==============================================================================
# NOVO BLOCO: ANÁLISE INVESTIGATIVA DE NEGATIVAS (EXPANSÃO) - CORRIGIDO
# ==============================================================================
st.markdown("---")
st.header("🔍 Diagnóstico Investigativo: Expansão e Negativas")
st.sidebar.header("2.5. Expansão e Negativas")

arquivo_negativas = st.sidebar.file_uploader(
    "Planilha de Negativas (Expansão):", 
    type=["xlsx", "xls", "csv"], 
    key="neg_file"
)

if arquivo_negativas is not None:
    try:
        # Carregamento robusto
        if "csv" in arquivo_negativas.name.lower():
            df_neg = pd.read_csv(arquivo_negativas, decimal=',', engine='python')
        else:
            df_neg = pd.read_excel(arquivo_negativas)

        # Filtro de lojas negativas
        df_neg_lojas = df_neg[df_neg['RO Mês'] < 0].copy() if 'RO Mês' in df_neg.columns else df_neg.copy()

        # --- 1. KPIs GLOBAIS NO TOPO ---
        st.subheader("📊 Visão Consolidada do Prejuízo")
        k1, k2, k3, k4, k5 = st.columns(5)
        
        preju_mes = df_neg_lojas['RO Mês'].sum() if 'RO Mês' in df_neg_lojas.columns else 0
        preju_acum = df_neg_lojas['RO Acum'].sum() if 'RO Acum' in df_neg_lojas.columns else 0
        multas = df_neg_lojas['Multa rescisória atual'].sum() if 'Multa rescisória atual' in df_neg_lojas.columns else 0
        
        # Cálculo de CMV Médio Estimado (Considerando Markup Reverso se a coluna não existir)
        # Se você tiver uma coluna CMV específica, altere 'CMV' aqui
        cmv_medio = 65.0 # Valor padrão caso não encontre
        if 'CMV' in df_neg_lojas.columns:
            cmv_medio = df_neg_lojas['CMV'].mean()
        
        k1.metric("Lojas em Negativo", f"{len(df_neg_lojas)}")
        k2.metric("Prejuízo Mês", f"R$ {preju_mes:,.2f}")
        k3.metric("Prejuízo Acumulado", f"R$ {preju_acum:,.2f}")
        k4.metric("Total Multas", f"R$ {multas:,.2f}")
        k5.metric("CMV Médio", f"{cmv_medio:.1f}%")

        st.markdown("---")

        # --- 2. RANKING TOP 15 E DIAGNÓSTICO ---
        c_rank, c_diag = st.columns([1.5, 1])
        
        with c_rank:
            st.write("🏆 **Top 15 Lojas com Maior Prejuízo (Mês)**")
            if 'RO Mês' in df_neg_lojas.columns:
                top_15 = df_neg_lojas.nsmallest(15, 'RO Mês').copy()
                # Colunas para exibir
                cols_show = [c for c in ['Desc_CC', 'RO Mês', 'RO Acum', 'Vagas', 'Posição Loja'] if c in top_15.columns]
                st.dataframe(top_15[cols_show].style.format({'RO Mês': 'R$ {:,.2f}', 'RO Acum': 'R$ {:,.2f}'}), 
                             use_container_width=True, hide_index=True)

        with c_diag:
            st.write("🧬 **Fatores de Risco Detectados**")
            # Análise de Vagas
            if 'Vagas' in df_neg_lojas.columns:
                vagas_stats = df_neg_lojas['Vagas'].value_counts()
                st.write(f"🚗 **Estacionamento:** {vagas_stats.get('Não', 0)} lojas negativas não possuem vagas.")
            
            # Análise de Posicionamento
            if 'Posição Loja' in df_neg_lojas.columns:
                pos_rank = df_neg_lojas.groupby('Posição Loja')['RO Mês'].mean().sort_values()
                st.write(f"📍 **Pior Posição Média:** {pos_rank.index[0]}")
                st.plotly_chart(px.bar(pos_rank, orientation='h', title="Prejuízo Médio por Posição", color_discrete_sequence=['#EF553B']), use_container_width=True)

        # --- 3. COMPARAÇÕES ADICIONAIS ---
        st.markdown("### 📊 Comparações de Infraestrutura vs Resultado")
        ca1, ca2 = st.columns(2)
        
        with ca1:
            if 'Próximo a mercado' in df_neg_lojas.columns:
                fig_mkt = px.box(df_neg_lojas, x='Próximo a mercado', y='RO Mês', title="Impacto: Proximidade com Mercados")
                st.plotly_chart(fig_mkt, use_container_width=True)
        
        with ca2:
            # Correlação de Concorrência (CORREÇÃO DO ERRO AQUI)
            conc_cols = ['Qtd_SaoJoao', 'Qtd_Independentes', 'Qtd_Total_Redes', 'Qtd_Panvel', 'Qtd_Raia']
            # Filtra apenas colunas que existem e garante que os nomes sejam strings
            existentes = [str(c) for c in df_neg_lojas.columns if any(x in str(c) for x in conc_cols)]
            
            if existentes and 'RO Mês' in df_neg_lojas.columns:
                corr = df_neg_lojas[existentes + ['RO Mês']].corr()['RO Mês'].sort_values()
                st.write("**Correlação Concorrência vs Resultado**")
                st.dataframe(corr.drop('RO Mês', errors='ignore'), use_container_width=True)

    except Exception as e:
        st.error(f"Erro no Diagnóstico de Expansão: {e}")


# 4. ANÁLISE FINANCEIRA (DRE)
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")
st.sidebar.header("3. Relatórios Financeiros")

if "dre_file" in st.session_state and st.session_state.dre_file:
    nomes_arquivos = [f.name for f in st.session_state.dre_file]
    opcoes_filtro = ["Todas"] + nomes_arquivos
    selecionados = st.sidebar.multiselect("Filtrar Unidades:", opcoes_filtro, default="Todas")
else:
    selecionados = ["Todas"]

arquivos_dre = st.sidebar.file_uploader(
    "Upload de arquivos DRE:", 
    type=["xlsx", "xls", "csv"], 
    key="dre_file",
    accept_multiple_files=True
)

if arquivos_dre:
    if "Todas" in selecionados or not selecionados:
        arquivos_para_processar = arquivos_dre
    else:
        arquivos_para_processar = [f for f in arquivos_dre if f.name in selecionados]

    for arquivo_dre in arquivos_para_processar:
        try:
            st.markdown(f"### 🏢 Unidade: {arquivo_dre.name}")
            df_dre_raw = pd.read_excel(arquivo_dre, header=None)
            
            termos = {
                "RB": "Receita Bruta", "RL": "Receita Líquida", "MC": "Margem de Contribuição",
                "PVL": "Perdas Vencidos Liquido", "DISC": "Discrepância _ Estoque",
                "FOLHA": "Despesas Folha", "ADM": "Despesas ADM", "OPER": "Despesas Operação",
                "RES": "Resultado Operacional", "CMV": "CMV"
            }
            
            indices = {}
            for chave, texto in termos.items():
                match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains(texto, case=False, na=False)]
                if not match.empty: indices[chave] = match.index[0]

            def pegar_v(chave):
                if chave in indices:
                    val = df_dre_raw.iloc[indices[chave], 3] 
                    return clean_numeric(val)
                return 0.0

            vals = {k: pegar_v(k) for k in termos.keys()}
            receita_base = vals['RL'] if vals['RL'] > 0 else (vals['RB'] if vals['RB'] > 0 else 1.0)
            perdas_totais = abs(vals['PVL']) + abs(vals['DISC'])

            c1, c2, c3, c4, c5 = st.columns(5) 
            c1.metric("Receita Líquida", f"R$ {vals['RL']:,.2f}")
            c2.metric("Margem Contrib.", f"R$ {vals['MC']:,.2f}")
            c3.metric("Resultado Oper.", f"R$ {vals['RES']:,.2f}", delta_color="normal" if vals['RES'] >= 0 else "inverse")
            c4.metric("Quebras/Perdas", f"R$ {perdas_totais:,.2f}")
            perc_cmv_head = (abs(vals['CMV']) / receita_base) * 100
            c5.metric("CMV", f"R$ {abs(vals['CMV']):,.2f}", delta=f"{perc_cmv_head:.1f}%")

            col_diag, col_graf = st.columns([1, 1])
            with col_diag:
                perc_margem = (vals['MC'] / receita_base) * 100
                perc_perda = (perdas_totais / receita_base) * 100
                if vals['RES'] < 0: st.error(f"🔴 Déficit operacional de R$ {abs(vals['RES']):,.2f}")
                if perc_margem < 35: st.warning(f"⚠️ Margem Baixa: {perc_margem:.2f}% (Meta: 35%)")
                if perc_perda > 1.5: st.warning(f"⚠️ Quebra Elevada: {perc_perda:.2f}% (Meta: 0,66%)")

            with col_graf:
                df_gastos = pd.DataFrame({
                    "Conta": ["Folha", "ADM", "Operação", "Quebra"],
                    "Valor": [abs(vals['FOLHA']), abs(vals['ADM']), abs(vals['OPER']), perdas_totais]
                })
                st.plotly_chart(px.pie(df_gastos, values='Valor', names='Conta', hole=0.4, title=f"Distribuição de Custos"), use_container_width=True)

            st.subheader("DRE Detalhado")
            df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")
            cols_valor = [i for i in range(3, len(df_exibicao.columns), 2)]
            cols_percent = [i for i in range(2, len(df_exibicao.columns), 2) if i not in cols_valor]

            def formatar_estilo_celula(val, tipo):
                num = clean_numeric(val)
                if num == 0 and (val == "" or val == "-"): return val
                return f"{num:.2f}%" if tipo == "pct" else f"R$ {num:,.2f}"

            def aplicar_estilo_mestre(row):
                styles = [''] * len(row)
                texto = str(row.iloc[1]).upper()
                if any(c in texto for c in ["RECEITA LÍQUIDA", "MARGEM DE CONTRIBUIÇÃO", "RESULTADO OPERACIONAL"]):
                    styles = ['background-color: #f8f9fa; font-weight: bold;'] * len(row)
                if "RESULTADO OPERACIONAL" in texto:
                    for i in range(3, len(row)):
                        if clean_numeric(row.iloc[i]) > 0:
                            styles[i] = 'background-color: #c8e6c9; color: #2e7d32; font-weight: bold;'
                return styles

            df_final = df_exibicao.style.apply(aplicar_estilo_mestre, axis=1)
            for col_idx in cols_percent:
                df_final = df_final.format(lambda x: formatar_estilo_celula(x, "pct"), 
                                         subset=pd.IndexSlice[2:, df_exibicao.columns[col_idx]])
            for col_idx in cols_valor:
                df_final = df_final.format(lambda x: formatar_estilo_celula(x, "val"), 
                                         subset=pd.IndexSlice[2:, df_exibicao.columns[col_idx]])
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # --- AJUSTE CORRIGIDO: PONTO DE EQUILÍBRIO ---
            meses_positivos = 0
            p_equilibrio, v_alvo_sugerida = 0.0, 0.0
            cmv_exibicao_formatado = 0.0
            
            if "RES" in indices:
                row_res = df_dre_raw.iloc[indices["RES"]]
                for i in range(3, len(row_res), 2):
                    if clean_numeric(row_res[i]) > 0: 
                        meses_positivos += 1
                
                try:
                    faturamento_atual = clean_numeric(df_dre_raw.iloc[indices["RL"], 29])
                    resultado_atual = clean_numeric(row_res[29])
                    cmv_bruto = clean_numeric(df_dre_raw.iloc[indices["CMV"], 30])
                    
                    cmv_para_calculo = abs(cmv_bruto)
                    if cmv_para_calculo > 1: cmv_para_calculo = cmv_para_calculo / 100
                    cmv_exibicao_formatado = cmv_para_calculo * 100
                    
                    margem_cont_real = 1 - cmv_para_calculo
                    if margem_cont_real > 0:
                        p_equilibrio = faturamento_atual + (abs(resultado_atual) / margem_cont_real)
                    else:
                        p_equilibrio = 0.0

                    v_alvo_sugerida = faturamento_atual + (abs(resultado_atual) / 0.35) 
                except:
                    p_equilibrio, v_alvo_sugerida = 0.0, 0.0

            r1, r2, r3 = st.columns(3)
            r1.info(f"**Histórico Positivo:** {meses_positivos} meses")
            r2.success(f"**Ponto de Equilíbrio CMV {cmv_exibicao_formatado:.0f}%:** R$ {p_equilibrio:,.2f}")
            r3.warning(f"**Venda Alvo Sugerida CMV 65%:** R$ {v_alvo_sugerida:,.2f}")
            st.markdown("---")

        except Exception as e:
            st.error(f"Erro ao processar {arquivo_dre.name}: {e}")
