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

# --- ESTADOS COMPARTILHADOS ---
taxas = []

# 2. PROJEÇÃO DE CRESCIMENTO (SEÇÃO 1)
st.sidebar.header("1. Parâmetros de Projeção")
arquivo_subido = st.sidebar.file_uploader(
    "Taxas de Crescimento:", 
    type=["xlsx", "xls", "csv"], 
    key="proj_file"
)

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

            st.header("Análise de Maturação")
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

df_loja_global = None
if arquivo_historico is not None:
    try:
        df_hist = pd.read_csv(arquivo_historico, decimal='.', engine='python') if "csv" in arquivo_historico.name.lower() else pd.read_excel(arquivo_historico)

        if 'Desc_Filial' in df_hist.columns:
            filiais = sorted(df_hist['Desc_Filial'].unique())
            st.header("Análise de Histórico")
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
            df_loja_global = df_loja # Para uso no Dashboard Consolidado
            
            fig_hist = px.bar(df_loja, x='Mes_PT', y='Mercadoria', title=f"Realizado vs Projetado: {filial_sel}", template="plotly_white", text='Valor_Texto') 
            fig_hist.add_scatter(x=df_loja['Mes_PT'], y=df_loja['Crescimento_Esperado'], mode='lines+markers', name='Projeção Teórica', line=dict(color='orange', width=3))
            fig_hist.update_traces(marker_color='#3366CC', textposition='outside', selector=dict(type='bar'))
            st.plotly_chart(fig_hist, use_container_width=True)
    except Exception as e:
        st.error(f"Erro no histórico: {e}")

# --- SEÇÃO 3: ANÁLISE DE LOJAS NEGATIVAS ---
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
    arquivos_para_processar = arquivos_dre if ("Todas" in selecionados or not selecionados) else [f for f in arquivos_dre if f.name in selecionados]

    for arquivo_dre in arquivos_para_processar:
        try:
            st.markdown(f"### Unidade: {arquivo_dre.name}")
            df_dre_raw = pd.read_excel(arquivo_dre, header=None)
            termos = {"RB": "Receita Bruta", "RL": "Receita Líquida", "MC": "Margem de Contribuição", "PVL": "Perdas Vencidos Liquido", "DISC": "Discrepância _ Estoque", "FOLHA": "Despesas Folha", "ADM": "Despesas ADM", "OPER": "Despesas Operação", "RES": "Resultado Operacional", "CMV": "CMV"}
            indices = {k: df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains(v, case=False, na=False)].index[0] for k, v in termos.items() if not df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains(v, case=False, na=False)].empty}

            def pegar_v(chave): return clean_numeric(df_dre_raw.iloc[indices[chave], 3]) if chave in indices else 0.0
            vals = {k: pegar_v(k) for k in termos.keys()}
            receita_base = vals['RL'] if vals['RL'] > 0 else 1.0
            perdas_totais = abs(vals['PVL']) + abs(vals['DISC'])

            c1, c2, c3, c4, c5 = st.columns(5) 
            c1.metric("Receita Líquida", f"R$ {vals['RL']:,.2f}")
            c2.metric("Margem Contrib.", f"R$ {vals['MC']:,.2f}")
            c3.metric("Resultado Oper.", f"R$ {vals['RES']:,.2f}", delta_color="normal" if vals['RES'] >= 0 else "inverse")
            c4.metric("Quebras/Perdas", f"R$ {perdas_totais:,.2f}")
            perc_cmv_head = (abs(vals['CMV']) / receita_base) * 100
            c5.metric("CMV", f"R$ {abs(vals['CMV']):,.2f}", delta=f"{perc_cmv_head:.1f}%")

            # Dashboard Compacto Detalhado
            st.dataframe(df_dre_raw.dropna(axis=1, how='all').fillna(""), use_container_width=True, hide_index=True)
        except Exception as e:
            st.error(f"Erro no DRE {arquivo_dre.name}: {e}")

# --- NOVO: 5. DASHBOARD EXECUTIVO CONSOLIDADO (CONFORME IMAGEM) ---
st.markdown("---")
st.header("5. Dashboard Executivo Consolidado")
st.sidebar.header("5. Configuração Executiva")

if arquivos_dre and arquivo_historico:
    escolha_dre = st.selectbox("Selecione o DRE para o Dashboard Executivo:", [f.name for f in arquivos_dre])
    
    # Processamento dos dados específicos para o Dashboard Consolidado
    arq_exec = [f for f in arquivos_dre if f.name == escolha_dre][0]
    df_dre_exec = pd.read_excel(arq_exec, header=None)
    
    termos_exec = {"RB": "Receita Bruta", "RL": "Receita Líquida", "MC": "Margem de Contribuição", "PVL": "Perdas Vencidos Liquido", "DISC": "Discrepância _ Estoque", "FOLHA": "Despesas Folha", "ADM": "Despesas ADM", "OPER": "Despesas Operação", "RES": "Resultado Operacional", "CMV": "CMV"}
    indices_exec = {k: df_dre_exec[df_dre_exec.iloc[:, 1].astype(str).str.strip().str.contains(v, case=False, na=False)].index[0] for k, v in termos_exec.items() if not df_dre_exec[df_dre_exec.iloc[:, 1].astype(str).str.strip().str.contains(v, case=False, na=False)].empty}
    
    def get_v_exec(chave): return clean_numeric(df_dre_exec.iloc[indices_exec[chave], 3]) if chave in indices_exec else 0.0
    v_exec = {k: get_v_exec(k) for k in termos_exec.keys()}
    rec_exec = v_exec['RL'] if v_exec['RL'] > 0 else 1.0
    quebra_exec = abs(v_exec['PVL']) + abs(v_exec['DISC'])

    # LAYOUT IGUAL À IMAGEM ANEXADA
    st.subheader(f"Unidade: {escolha_dre}")
    
    # KPIs Topo
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Receita Líquida", f"R$ {v_exec['RL']:,.2f}")
    k2.metric("Margem Contrib.", f"R$ {v_exec['MC']:,.2f}")
    k3.metric("Resultado Oper.", f"R$ {v_exec['RES']:,.2f}")
    k4.metric("Quebras/Perdas", f"R$ {quebra_exec:,.2f}")
    k5.metric("CMV", f"R$ {abs(v_exec['CMV']):,.2f}", delta=f"{(abs(v_exec['CMV'])/rec_exec)*100:.1f}%", delta_color="off")

    col_esq, col_dir = st.columns([1.2, 1])

    with col_esq:
        # Alertas
        if v_exec['RES'] < 0:
            st.error(f"Déficit operacional de R$ {abs(v_exec['RES']):,.2f}")
        
        margem_p = (v_exec['MC'] / rec_exec) * 100
        if margem_p < 35:
            st.warning(f"Margem Baixa: {margem_p:.2f}% (Meta: 35%)")
        
        # Gráfico de Barras (Histórico)
        if df_loja_global is not None:
            fig_exec_bar = px.bar(df_loja_global, x='Mes_PT', y='Mercadoria', 
                                 title=f"Realizado vs Projetado: {filial_sel}", 
                                 template="plotly_white", text='Valor_Texto')
            fig_exec_bar.add_scatter(x=df_loja_global['Mes_PT'], y=df_loja_global['Crescimento_Esperado'], 
                                    mode='lines+markers', name='Projeção Teórica', line=dict(color='orange', width=3))
            fig_exec_bar.update_layout(height=400, showlegend=True)
            st.plotly_chart(fig_exec_bar, use_container_width=True)

    with col_dir:
        # Gráfico Rosca de Custos
        df_custos_exec = pd.DataFrame({
            "Conta": ["Folha", "ADM", "Operação", "Quebra"],
            "Valor": [abs(v_exec['FOLHA']), abs(v_exec['ADM']), abs(v_exec['OPER']), quebra_exec]
        })
        fig_donut = px.pie(df_custos_exec, values='Valor', names='Conta', hole=0.5, 
                          title="Distribuição de Custos", color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_donut.update_layout(height=350)
        st.plotly_chart(fig_donut, use_container_width=True)

        # Info Boxes (Bottom Right)
        meses_pos = 0
        if "RES" in indices_exec:
            for i in range(3, 30, 2):
                if clean_numeric(df_dre_exec.iloc[indices_exec["RES"], i]) > 0: meses_pos += 1
        
        st.info(f"**Histórico Positivo:** {meses_pos} meses")
        
        # Cálculo de Equilíbrio
        cmv_p = (abs(v_exec['CMV'])/rec_exec)
        mc_p = 1 - cmv_p
        peq = v_exec['RL'] + (abs(v_exec['RES']) / mc_p) if mc_p > 0 else 0
        st.success(f"**Ponto de Equilíbrio CMV {cmv_p*100:.0f}%:** R$ {peq:,.2f}")
        
        valvo = v_exec['RL'] + (abs(v_exec['RES']) / 0.35)
        st.warning(f"**Venda Alvo Sugerida CMV 65%:** R$ {valvo:,.2f}")

else:
    st.info("Para visualizar o Dashboard Executivo (Seção 5), certifique-se de carregar tanto o Histórico de Vendas quanto os arquivos de DRE.")
