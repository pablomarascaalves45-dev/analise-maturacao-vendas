import pandas as pd
import plotly.express as px
import streamlit as st
import io

# ==============================================================================
# 1. CONFIGURAÇÃO DO DASHBOARD
# ==============================================================================
st.set_page_config(page_title="Gestão de Maturação e DRE", layout="wide")

st.title("Sistema de Análise: Expansão e Performance")
st.markdown("---")

def clean_numeric(val):
    if pd.isna(val) or val == "" or val == "-" or val == " ":
        return 0.0
    try:
        s = str(val).replace('R$', '').replace('%', '').replace(' ', '').strip()
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except:
        return 0.0

# ==============================================================================
# 2. PROJEÇÃO DE CRESCIMENTO (MATURAÇÃO)
# ==============================================================================
st.header("1. Projeção de Maturação")
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

# ==============================================================================
# 2. DIAGNÓSTICO INVESTIGATIVO (PLANILHA DE NEGATIVAS)
# ==============================================================================
st.markdown("---")
st.header("2. Diagnóstico Investigativo: Expansão e Negativas")
st.sidebar.header("2. Diagnóstico de Negativas")

arquivo_negativas = st.sidebar.file_uploader(
    "Planilha de Negativas/Expansão:", 
    type=["xlsx", "xls", "csv"], 
    key="neg_file_diag"
)

if arquivo_negativas is not None:
    try:
        if "csv" in arquivo_negativas.name.lower():
            df_neg = pd.read_csv(arquivo_negativas, decimal=',', engine='python')
        else:
            df_neg = pd.read_excel(arquivo_negativas)

        # Normalização de Colunas (Remove espaços e caracteres invisíveis)
        df_neg.columns = [str(c).strip() for c in df_neg.columns]
        
        # Mapeamento dinâmico de colunas financeiras
        def find_column(options, current_cols):
            for opt in options:
                if opt in current_cols: return opt
            return None

        col_ro_mes = find_column(['RO Mês', 'RO Mes', 'Resultado Operacional Mês'], df_neg.columns) or df_neg.columns[5]
        col_ro_acum = find_column(['RO Acum', 'RO Acumulado', 'Resultado Acumulado'], df_neg.columns) or df_neg.columns[7]
        col_multa = find_column(['Multa rescisória atual', 'Multa'], df_neg.columns) or df_neg.columns[12]

        # Conversão numérica
        df_neg[col_ro_mes] = df_neg[col_ro_mes].apply(clean_numeric)
        df_neg[col_ro_acum] = df_neg[col_ro_acum].apply(clean_numeric)
        df_neg[col_multa] = df_neg[col_multa].apply(clean_numeric)

        # Cálculo das Métricas
        total_lojas = len(df_neg)
        prejuizo_mes = df_neg[df_neg[col_ro_mes] < 0][col_ro_mes].sum()
        prejuizo_acum = df_neg[df_neg[col_ro_acum] < 0][col_ro_acum].sum()
        total_multas = df_neg[col_multa].sum()

        # Exibição dos KPIs
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total de Lojas", f"{total_lojas}")
        k2.metric("Prejuízo (Mês)", f"R$ {prejuizo_mes:,.2f}", delta_color="inverse")
        k3.metric("Prejuízo (Acumulado)", f"R$ {prejuizo_acum:,.2f}", delta_color="inverse")
        k4.metric("Soma das Multas", f"R$ {total_multas:,.2f}")

        # Gráficos de Diagnóstico
        g1, g2 = st.columns(2)
        with g1:
            st.write("**📡 Densidade Competitiva vs Resultado**")
            col_redes = [c for c in df_neg.columns if 'Total Redes' in c or 'Qtd_Total' in c]
            if col_redes:
                fig_comp = px.scatter(df_neg, x=col_redes[0], y=col_ro_mes, 
                                     hover_name='Desc_CC' if 'Desc_CC' in df_neg.columns else None,
                                     trendline="ols", template="plotly_white",
                                     title="Impacto da Concorrência no RO")
                st.plotly_chart(fig_comp, use_container_width=True)

        with g2:
            st.write("**🏆 Top Concorrentes Próximos**")
            col_conc = [c for c in df_neg.columns if any(x in str(c) for x in ["SaoJoao", "Panvel", "Raia", "Nissei", "Pacheco"])]
            if col_conc:
                soma_conc = df_neg[col_conc].apply(pd.to_numeric, errors='coerce').sum().sort_values(ascending=False).head(10)
                fig_conc = px.bar(soma_conc, orientation='h', color_discrete_sequence=['#EF553B'], title="Presença de Redes")
                st.plotly_chart(fig_conc, use_container_width=True)

        st.write("**📋 Detalhamento das Unidades Analisadas**")
        st.dataframe(df_neg.sort_values(by=col_ro_mes), use_container_width=True)

    except Exception as e:
        st.error(f"Erro no diagnóstico de negativas: {e}")

# ==============================================================================
# 3. COMPARATIVO REAL
# ==============================================================================
st.markdown("---")
st.header("3. Comparativo Realizado vs. Projetado")
st.sidebar.header("3. Dados Históricos")
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
# 4. ANÁLISE FINANCEIRA (DRE)
# ==============================================================================
st.markdown("---")
st.header("4. Análise de DRE e Rentabilidade")
st.sidebar.header("4. Relatórios Financeiros")

arquivos_dre = st.sidebar.file_uploader(
    "Upload de arquivos DRE:", 
    type=["xlsx", "xls", "csv"], 
    key="dre_file",
    accept_multiple_files=True
)

if arquivos_dre:
    for arquivo_dre in arquivos_dre:
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

            df_final = df_exibicao.style
            for col_idx in cols_percent:
                df_final = df_final.format(lambda x: formatar_estilo_celula(x, "pct"), subset=pd.IndexSlice[2:, df_exibicao.columns[col_idx]])
            for col_idx in cols_valor:
                df_final = df_final.format(lambda x: formatar_estilo_celula(x, "val"), subset=pd.IndexSlice[2:, df_exibicao.columns[col_idx]])
            st.dataframe(df_final, use_container_width=True, hide_index=True)

            # --- PROJEÇÕES FINAIS ---
            meses_positivos = 0
            if "RES" in indices:
                row_res = df_dre_raw.iloc[indices["RES"]]
                for i in range(3, len(row_res), 2):
                    if clean_numeric(row_res[i]) > 0: meses_positivos += 1
                
                try:
                    f_at = clean_numeric(df_dre_raw.iloc[indices["RL"], 29])
                    res_at = clean_numeric(row_res[29])
                    cmv_at = abs(clean_numeric(df_dre_raw.iloc[indices["CMV"], 30]))
                    if cmv_at > 1: cmv_at /= 100
                    p_eq = f_at + (abs(res_at) / (1 - cmv_at)) if (1-cmv_at) > 0 else 0
                    v_alvo = f_at + (abs(res_at) / 0.35)
                    
                    r1, r2, r3 = st.columns(3)
                    r1.info(f"**Histórico Positivo:** {meses_positivos} meses")
                    r2.success(f"**Ponto de Equilíbrio (CMV {cmv_at*100:.0f}%):** R$ {p_eq:,.2f}")
                    r3.warning(f"**Venda Alvo (Margem 35%):** R$ {v_alvo:,.2f}")
                except: pass
            st.markdown("---")

        except Exception as e:
            st.error(f"Erro ao processar {arquivo_dre.name}: {e}")
