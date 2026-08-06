import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DO DASHBOARD
st.set_page_config(page_title="Gestão de Maturação, DRE e Performance", layout="wide")

st.title("Sistema de Análise: Expansão e Performance")
st.markdown("---")

# --- FUNÇÕES DE UTILIDADE ---
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

@st.cache_data
def load_data_negativas(file):
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols_financeiras = ['RO Mês', 'RO Acum', 'Aluguel Mês', '%RO Mês', '%RO Acum', '%Aluguel Mês', 'Multa rescisória atual']
    
    for col in cols_financeiras:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = (df[col].astype(str)
                           .str.replace('R$', '', regex=False)
                           .str.replace('%', '', regex=False)
                           .str.replace('.', '', regex=False)
                           .str.replace(',', '.', regex=False)
                           .str.strip())
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            if col.startswith('%'):
                if df[col].abs().mean() < 1.0:
                    df[col] = df[col] * 100
    return df

# 2. PROJEÇÃO DE CRESCIMENTO (SEÇÃO 1)
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

# 3. COMPARATIVO REAL (SEÇÃO 2)
st.markdown("---")
st.sidebar.header("2. Dados Históricos")
arquivo_historico = st.sidebar.file_uploader(
    "Histórico de Vendas Realizadas:", 
    type=["xlsx", "xls", "csv"], 
    key="hist_file"
)

df_loja_selecionada = None
filial_nome_selecionada = ""

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
            
            df_loja_selecionada = df_loja
            filial_nome_selecionada = filial_sel
            
            fig_hist = px.bar(df_loja, x='Mes_PT', y='Mercadoria', title=f"Realizado vs Projetado: {filial_sel}", template="plotly_white", text='Valor_Texto') 
            fig_hist.add_scatter(x=df_loja['Mes_PT'], y=df_loja['Crescimento_Esperado'], mode='lines+markers', name='Projeção Teórica', line=dict(color='orange', width=3))
            fig_hist.update_traces(marker_color='#3366CC', textposition='outside', selector=dict(type='bar'))
            st.plotly_chart(fig_hist, use_container_width=True)
    except Exception as e:
        st.error(f"Erro no histórico: {e}")

# 4. ANÁLISE DE LOJAS NEGATIVAS (SEÇÃO 3)
st.markdown("---")
st.header("Análise Estratégica: Performance de Unidades Negativas")
st.sidebar.header("3. Unidades Negativas")

arquivo_negativas = st.sidebar.file_uploader(
    "Planilha de Lojas Negativas:", 
    type=["xlsx", "xls"], 
    key="negativas_file"
)

if arquivo_negativas:
    try:
        df = load_data_negativas(arquivo_negativas)
        
        total_prejuizo_mes = df['RO Mês'].sum()
        total_prejuizo_acum = df['RO Acum'].sum()
        qtd_lojas = len(df) 
        media_aluguel_perc = df['%Aluguel Mês'].mean()

        c0, c1, c2, c3 = st.columns(4)
        c0.metric("Lojas Analisadas", f"{qtd_lojas}")
        c1.metric("Prejuízo Total Mês", f"R$ {total_prejuizo_mes:,.2f}")
        c2.metric("Prejuízo Acumulado", f"R$ {total_prejuizo_acum:,.2f}")
        c3.metric("Média % Aluguel", f"{media_aluguel_perc:.2f}%")

        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Top 10 Unidades Críticas (Mês)")
            top_negativas = df.nsmallest(10, 'RO Mês')
            fig_neg = px.bar(top_negativas, x='RO Mês', y='Desc_CC', orientation='h',
                             color='RO Mês', color_continuous_scale='Reds_r')
            fig_neg.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_neg, use_container_width=True)

        with col_graf2:
            st.subheader("Aluguel vs Resultado (Mês)")
            fig_scat = px.scatter(df, x='%Aluguel Mês', y='RO Mês', hover_name='Desc_CC', 
                                  size='Aluguel Mês', color='Diretor' if 'Diretor' in df.columns else None)
            fig_scat.update_layout(xaxis_ticksuffix="%")
            st.plotly_chart(fig_scat, use_container_width=True)

        st.markdown("---")
        
        col_graf3, col_graf4 = st.columns(2)
        with col_graf3:
            st.subheader("Top 10 Unidades Críticas (Acumulado)")
            top_negativas_acum = df.nsmallest(10, 'RO Acum')
            fig_neg_acum = px.bar(top_negativas_acum, x='RO Acum', y='Desc_CC', orientation='h',
                                  color='RO Acum', color_continuous_scale='Reds_r')
            fig_neg_acum.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_neg_acum, use_container_width=True)

        with col_graf4:
            st.subheader("Aluguel vs Resultado (Acumulado)")
            fig_scat_acum = px.scatter(df, x='%Aluguel Mês', y='RO Acum', hover_name='Desc_CC', 
                                       size='Aluguel Mês', color='Diretor' if 'Diretor' in df.columns else None)
            fig_scat_acum.update_layout(xaxis_ticksuffix="%")
            st.plotly_chart(fig_scat_acum, use_container_width=True)

        st.markdown("---")
        col_rank1, col_rank2 = st.columns(2)
        with col_rank1:
            st.subheader("Top 10 Maiores Aluguéis")
            top_aluguel = df.nlargest(10, 'Aluguel Mês')
            fig_aluguel = px.bar(top_aluguel, x='Aluguel Mês', y='Desc_CC', orientation='h',
                                 color='Aluguel Mês', color_continuous_scale='Blues')
            st.plotly_chart(fig_aluguel, use_container_width=True)

        with col_rank2:
            st.subheader("Top 10 Maiores Multas")
            if 'Multa rescisória atual' in df.columns:
                top_multa = df.nlargest(10, 'Multa rescisória atual')
                fig_multa = px.bar(top_multa, x='Multa rescisória atual', y='Desc_CC', orientation='h',
                                   color='Multa rescisória atual', color_continuous_scale='Oranges')
                st.plotly_chart(fig_multa, use_container_width=True)

        st.markdown("---")
        st.subheader("Análise Qualitativa: Características dos Pontos Críticos")
        cols_perfil = ["Posição Loja", "Próximo a mercado", "Vagas", "Loja atualizada"]
        cols_existentes = [c for c in cols_perfil if c in df.columns]

        if cols_existentes:
            c_p1, c_p2 = st.columns(2)
            for idx, col in enumerate(cols_existentes):
                target = c_p1 if idx % 2 == 0 else c_p2
                df_p = df[col].value_counts().reset_index()
                df_p.columns = [col, 'Quantidade']
                fig = px.pie(df_p, values='Quantidade', names=col, title=f"Perfil: {col}", hole=0.4)
                target.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("Polos Geradores de Tráfego")
        polos_lista = ["Aliment", "Ensin", "Saúd", "Banco", "Bem-est"]
        cols_polos_encontradas = [c for c in df.columns if any(p.lower() in c.lower() for p in polos_lista)]

        if cols_polos_encontradas:
            contagem_polos = {}
            for col in cols_polos_encontradas:
                filtro_presenca = df[col].astype(str).str.lower().isin(['sim', 'x', 's', '1', '1.0'])
                contagem_polos[col] = df[filtro_presenca].shape[0]
            
            df_polos = pd.DataFrame(list(contagem_polos.items()), columns=['Tipo de Polo', 'Incidência'])
            df_polos = df_polos.sort_values(by='Incidência', ascending=False)
            col_p1, col_p2 = st.columns([2, 1])
            with col_p1:
                fig_polos = px.bar(df_polos, x='Tipo de Polo', y='Incidência', 
                                  title="Presença de Polos Geradores nas Unidades Negativas",
                                  color='Incidência', color_continuous_scale='Viridis')
                st.plotly_chart(fig_polos, use_container_width=True)
            with col_p2:
                st.info("**Análise de Tráfego**")
                st.write("Esta visão demonstra quais tipos de estabelecimentos vizinhos são mais comuns nas lojas com RO negativo.")

        st.markdown("---")
        st.subheader("Análise de Concorrência: Impacto na Performance")
        concorrentes_lista = ["SaoJoao", "Independente", "Panvel", "Raia", "Morifarma", "Nissei", "PPCatarinense", "Pacheco", "FarmTrabalhador"]
        cols_conc_encontradas = [c for c in df.columns if any(conc.lower() in c.lower() for conc in concorrentes_lista)]

        if cols_conc_encontradas:
            contagem_concorrentes = {}
            for col in cols_conc_encontradas:
                filtro_presenca = df[col].astype(str).str.lower().isin(['sim', 'x', 's', '1', '1.0'])
                contagem_concorrentes[col] = df[filtro_presenca].shape[0]
            
            df_conc = pd.DataFrame(list(contagem_concorrentes.items()), columns=['Rede', 'Lojas Próximas'])
            df_conc = df_conc.sort_values(by='Lojas Próximas', ascending=False)
            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                fig_conc = px.bar(df_conc, x='Rede', y='Lojas Próximas', 
                                  title="Incidência de Concorrentes nas Unidades Negativas",
                                  color='Lojas Próximas', color_continuous_scale='Turbo')
                st.plotly_chart(fig_conc, use_container_width=True)
            with col_c2:
                st.info("**Análise de Densidade**")
                st.write("O gráfico ao lado indica quais bandeiras concorrentes possuem maior sobreposição geográfica.")

        st.markdown("---")
        st.subheader("Cruzamento de Dados: Unidades Críticas Recorrentes")
        
        lojas_mes = set(top_negativas['Desc_CC'])
        lojas_acum = set(top_negativas_acum['Desc_CC'])
        lojas_repetidas = sorted(list(lojas_mes.intersection(lojas_acum)))
        
        if lojas_repetidas:
            st.write(f"Lojas presentes no Top 10 (Mês e Acumulado): {len(lojas_repetidas)}")
            cols_rep = st.columns(len(lojas_repetidas)) 
            
            for i, loja in enumerate(lojas_repetidas):
                dados_loja = df[df['Desc_CC'] == loja].iloc[0]
                
                conc_loja = {}
                for col in cols_conc_encontradas:
                    val = str(dados_loja[col]).lower()
                    if val in ['sim', 'x', 's', '1', '1.0']:
                        conc_loja[col] = 1
                top_3_conc = sorted(conc_loja.items(), key=lambda x: x[1], reverse=True)[:3]
                str_conc = " / ".join([f"{c[0]}: {c[1]}" for c in top_3_conc]) if top_3_conc else "Nenhum mapeado"

                polos_loja = [col for col in cols_polos_encontradas if str(dados_loja[col]).lower() in ['sim', 'x', 's', '1', '1.0']]
                str_polos = ", ".join(polos_loja[:3]) if polos_loja else "Nenhum mapeado"

                with cols_rep[i]:
                    st.info(f"""
                    **{loja}**
                    
                    **Financeiro:**
                    * RO Mês: R$ {dados_loja['RO Mês']:,.2f}
                    * RO Acum: R$ {dados_loja['RO Acum']:,.2f}
                    * Aluguel: R$ {dados_loja['Aluguel Mês']:,.2f}
                    
                    **Vizinhança:**
                    * 🏁 {str_conc}
                    * 📍 {str_polos}
                    """)
        else:
            st.write("Não há recorrência de lojas entre os rankings.")

        st.markdown("---")
        st.subheader("Demais Unidades com Performance Negativa")
        
        df_restante = df[~df['Desc_CC'].isin(lojas_repetidas)].copy()
        df_restante = df_restante.sort_values(by='RO Mês', ascending=True)
        
        if not df_restante.empty:
            cols_restante = st.columns(4)
            for idx, (_, dados_loja) in enumerate(df_restante.iterrows()):
                col_idx = idx % 4
                loja_nome = dados_loja['Desc_CC']
                
                conc_loja = {}
                for col in cols_conc_encontradas:
                    val = str(dados_loja[col]).lower()
                    if val in ['sim', 'x', 's', '1', '1.0']:
                        conc_loja[col] = 1
                top_3_conc = sorted(conc_loja.items(), key=lambda x: x[1], reverse=True)[:3]
                str_conc = " / ".join([f"{c[0]}: {c[1]}" for c in top_3_conc]) if top_3_conc else "Nenhum mapeado"

                polos_loja = [col for col in cols_polos_encontradas if str(dados_loja[col]).lower() in ['sim', 'x', 's', '1', '1.0']]
                str_polos = ", ".join(polos_loja[:3]) if polos_loja else "Nenhum mapeado"

                with cols_restante[col_idx]:
                    st.warning(f"""
                    **{loja_nome}**
                    
                    **Financeiro:**
                    * RO Mês: R$ {dados_loja['RO Mês']:,.2f}
                    * RO Acum: R$ {dados_loja['RO Acum']:,.2f}
                    * Aluguel: R$ {dados_loja['Aluguel Mês']:,.2f}
                    
                    **Vizinhança:**
                    * 🏁 {str_conc}
                    * 📍 {str_polos}
                    """)
        else:
            st.write("Não há outras unidades negativas registradas.")

    except Exception as e:
        st.error(f"Erro ao processar lojas negativas: {e}")
else:
    st.info("Faça o upload do arquivo de Lojas Negativas para ativar esta seção.")

# 5. ANÁLISE FINANCEIRA (DRE) (SEÇÃO 4)
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")
st.sidebar.header("4. Relatórios Financeiros")

arquivos_dre = st.sidebar.file_uploader(
    "Upload de arquivos DRE:", 
    type=["xlsx", "xls", "csv"], 
    key="dre_file_upload",
    accept_multiple_files=True
)

if arquivos_dre:
    nomes_arquivos = [f.name for f in arquivos_dre]
    selecionados = st.sidebar.multiselect("Filtrar Unidades DRE:", ["Todas"] + nomes_arquivos, default="Todas")

    if "Todas" in selecionados or not selecionados:
        arquivos_para_processar = arquivos_dre
    else:
        arquivos_para_processar = [f for f in arquivos_dre if f.name in selecionados]

    for arquivo_dre in arquivos_para_processar:
        try:
            st.markdown(f"### Unidade: {arquivo_dre.name}")
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
                if vals['RES'] < 0: st.error(f"Déficit operacional de R$ {abs(vals['RES']):,.2f}")
                if perc_margem < 35: st.warning(f"Margem Baixa: {perc_margem:.2f}% (Meta: 35%)")
                if perc_perda > 1.5: st.warning(f"Quebra Elevada: {perc_perda:.2f}% (Meta: 0,66%)")

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

        except Exception as e:
            st.error(f"Erro ao processar DRE ({arquivo_dre.name}): {e}")

# 6. MÓDULO ADICIONAL: ANÁLISE DE INAUGURAÇÕES HISTÓRICAS (SEÇÃO 5)
st.markdown("---")
st.header("Análise de Inaugurações e Maturação Histórica")
st.sidebar.header("5. Inaugurações")

arquivos_inauguracoes = st.sidebar.file_uploader(
    "Planilhas de Inaugurações (2021-2025):", 
    type=["xlsx", "xls"], 
    key="inaug_files",
    accept_multiple_files=True
)

if arquivos_inauguracoes:
    try:
        lista_dfs = []
        for file in arquivos_inauguracoes:
            df_inaug = pd.read_excel(file)
            df_inaug.columns = [str(c).strip() for c in df_inaug.columns]
            df_inaug['Arquivo_Origem'] = file.name
            lista_dfs.append(df_inaug)
        
        df_todas_inaug = pd.concat(lista_dfs, ignore_index=True)
        df_todas_inaug = df_todas_inaug[df_todas_inaug['Desc. Loja'].astype(str).str.lower() != 'total']
        
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total de Inaugurações Mapeadas", f"{len(df_todas_inaug)}")
        
        if 'Valor do Potencial' in df_todas_inaug.columns:
            df_todas_inaug['Valor do Potencial'] = df_todas_inaug['Valor do Potencial'].apply(clean_numeric)
            media_potencial = df_todas_inaug['Valor do Potencial'].mean()
            m_col2.metric("Média do Potencial de Mercado (VPM)", f"R$ {media_potencial:,.2f}")
            
        if 'Resultado Oper. Acum.' in df_todas_inaug.columns:
            df_todas_inaug['Resultado Oper. Acum.'] = df_todas_inaug['Resultado Oper. Acum.'].apply(clean_numeric)
            ro_medio = df_todas_inaug['Resultado Oper. Acum.'].mean()
            m_col3.metric("Resultado Operacional Acum. Médio", f"R$ {ro_medio:,.2f}")

        # Tabela interativa de busca por unidade
        st.subheader("Detalhamento por Unidade Inaugurada")
        col_lojas = sorted(df_todas_inaug['Desc. Loja'].astype(str).unique())
        loja_inaug_sel = st.selectbox("Selecione a Loja Inaugurada:", ["Todas"] + col_lojas)
        
        if loja_inaug_sel != "Todas":
            df_exib_inaug = df_todas_inaug[df_todas_inaug['Desc. Loja'] == loja_inaug_sel]
        else:
            df_exib_inaug = df_todas_inaug

        st.dataframe(df_exib_inaug[['Desc. Loja', 'Dt_Abertura', 'Valor do Potencial', 'Resultado Oper. Acum.', 'Arquivo_Origem']], use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar arquivos de inaugurações: {e}")
