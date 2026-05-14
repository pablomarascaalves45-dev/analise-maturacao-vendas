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

# Variável para armazenar dados da filial para a seção 5
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
            
            # Salva para uso na seção 5
            df_loja_selecionada = df_loja
            filial_nome_selecionada = filial_sel
            
            fig_hist = px.bar(df_loja, x='Mes_PT', y='Mercadoria', title=f"Realizado vs Projetado: {filial_sel}", template="plotly_white", text='Valor_Texto') 
            fig_hist.add_scatter(x=df_loja['Mes_PT'], y=df_loja['Crescimento_Esperado'], mode='lines+markers', name='Projeção Teórica', line=dict(color='orange', width=3))
            fig_hist.update_traces(marker_color='#3366CC', textposition='outside', selector=dict(type='bar'))
            st.plotly_chart(fig_hist, use_container_width=True)
    except Exception as e:
        st.error(f"Erro no histórico: {e}")

# 3. ANÁLISE DE LOJAS NEGATIVAS (SEÇÃO 3)
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

    except Exception as e:
        st.error(f"Erro ao processar lojas negativas: {e}")

# 4. ANÁLISE FINANCEIRA (DRE) (SEÇÃO 4)
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

            st.subheader("DRE Detalhado")
            df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")
            st.dataframe(df_exibicao, use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Erro ao processar {arquivo_dre.name}: {e}")

# --- NOVA SEÇÃO 5: DASHBOARD EXECUTIVO (CONFORME SOLICITADO) ---
st.markdown("---")
st.header("5. Dashboard Executivo Consolidado")

if arquivos_dre:
    # Opção para escolher o DRE e filtrar
    nomes_para_filtro = [f.name for f in arquivos_dre]
    escolha_dre_dash = st.selectbox("Selecione o DRE para o Dashboard Executivo:", nomes_para_filtro)
    
    # Processamento do arquivo selecionado
    arquivo_selecionado = [f for f in arquivos_dre if f.name == escolha_dre_dash][0]
    
    try:
        df_dre_dash = pd.read_excel(arquivo_selecionado, header=None)
        
        # Mapeamento de termos
        termos_dash = {
            "RB": "Receita Bruta", "RL": "Receita Líquida", "MC": "Margem de Contribuição",
            "PVL": "Perdas Vencidos Liquido", "DISC": "Discrepância _ Estoque",
            "FOLHA": "Despesas Folha", "ADM": "Despesas ADM", "OPER": "Despesas Operação",
            "RES": "Resultado Operacional", "CMV": "CMV"
        }
        
        indices_dash = {}
        for chave, texto in termos_dash.items():
            match = df_dre_dash[df_dre_dash.iloc[:, 1].astype(str).str.strip().str.contains(texto, case=False, na=False)]
            if not match.empty: indices_dash[chave] = match.index[0]

        def get_v_dash(chave):
            if chave in indices_dash:
                return clean_numeric(df_dre_dash.iloc[indices_dash[chave], 3])
            return 0.0

        v_dash = {k: get_v_dash(k) for k in termos_dash.keys()}
        rec_base_dash = v_dash['RL'] if v_dash['RL'] > 0 else 1.0
        perdas_dash = abs(v_dash['PVL']) + abs(v_dash['DISC'])

        # --- LINHA 1: MÉTRICAS PRINCIPAIS ---
        st.subheader(f"Unidade: {arquivo_selecionado.name}")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Receita Líquida", f"R$ {v_dash['RL']:,.2f}")
        c2.metric("Margem Contrib.", f"R$ {v_dash['MC']:,.2f}")
        c3.metric("Resultado Oper.", f"R$ {v_dash['RES']:,.2f}")
        c4.metric("Quebras/Perdas", f"R$ {perdas_dash:,.2f}")
        c5.metric("CMV", f"R$ {abs(v_dash['CMV']):,.2f}", f"{(abs(v_dash['CMV'])/rec_base_dash)*100:.1f}%")

        # --- LINHA 2: ALERTAS E PIE CHART ---
        col_alertas, col_vazio, col_pie = st.columns([1.5, 0.2, 1.3])
        
        with col_alertas:
            # Alertas baseados na imagem
            if v_dash['RES'] < 0:
                st.error(f"Déficit operacional de R$ {abs(v_dash['RES']):,.2f}")
            
            p_mc_dash = (v_dash['MC'] / rec_base_dash) * 100
            if p_mc_dash < 35:
                st.warning(f"Margem Baixa: {p_mc_dash:.2f}% (Meta: 35%)")
            
            p_perda_dash = (perdas_dash / rec_base_dash) * 100
            if p_perda_dash > 1.5:
                st.warning(f"Quebra Elevada: {p_perda_dash:.2f}% (Meta: 0.66%)")

        with col_pie:
            df_pie_dash = pd.DataFrame({
                "Conta": ["Folha", "ADM", "Operação", "Quebra"],
                "Valor": [abs(v_dash['FOLHA']), abs(v_dash['ADM']), abs(v_dash['OPER']), perdas_dash]
            })
            fig_pie_dash = px.pie(df_pie_dash, values='Valor', names='Conta', hole=0.5, 
                                 title="Distribuição de Custos",
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie_dash.update_layout(showlegend=True, margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig_pie_dash, use_container_width=True)

        # --- LINHA 3: GRÁFICO HISTÓRICO E INFOS ADICIONAIS ---
        col_hist_exec, col_infos_exec = st.columns([2, 1])

        with col_hist_exec:
            if df_loja_selecionada is not None:
                st.write(f"**Realizado vs Projetado: {filial_nome_selecionada}**")
                fig_exec = px.bar(df_loja_selecionada, x='Mes_PT', y='Mercadoria', template="plotly_white")
                fig_exec.add_scatter(x=df_loja_selecionada['Mes_PT'], y=df_loja_selecionada['Crescimento_Esperado'], 
                                     mode='lines+markers', name='Projeção Teórica', line=dict(color='orange'))
                fig_exec.update_layout(height=350, margin=dict(t=10, b=10))
                st.plotly_chart(fig_exec, use_container_width=True)
            else:
                st.info("Faça o upload do Histórico de Vendas (Seção 2) para visualizar o gráfico aqui.")

        with col_infos_exec:
            # Cálculos de equilíbrio baseados no DRE selecionado
            meses_pos = 0
            if "RES" in indices_dash:
                row_res_dash = df_dre_dash.iloc[indices_dash["RES"]]
                for i in range(3, len(row_res_dash), 2):
                    if clean_numeric(row_res_dash[i]) > 0: meses_pos += 1
            
            # Cálculo Ponto de Equilíbrio (Simplificado para o dash)
            try:
                cmv_val_calc = abs(v_dash['CMV']) / rec_base_dash
                m_calc = 1 - cmv_val_calc
                eq_dash = v_dash['RL'] + (abs(v_dash['RES']) / m_calc) if m_calc > 0 else 0
                alvo_dash = v_dash['RL'] + (abs(v_dash['RES']) / 0.35)
            except:
                eq_dash, alvo_dash = 0, 0

            st.write("") # Espaçador
            st.info(f"Histórico Positivo: {meses_pos} meses")
            st.success(f"Ponto de Equilíbrio CMV {(1-m_calc)*100:.0f}%: R$ {eq_dash:,.2f}")
            st.warning(f"Venda Alvo Sugerida CMV 65%: R$ {alvo_dash:,.2f}")

    except Exception as e:
        st.error(f"Erro ao gerar Dashboard Executivo: {e}")
else:
    st.info("Faça o upload de ao menos um arquivo DRE na Seção 4 para ativar o Dashboard Executivo.")
