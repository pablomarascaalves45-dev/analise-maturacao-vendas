import pandas as pd
import plotly.express as px
import streamlit as st
import io
from fpdf import FPDF
import datetime

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
    df.columns = df.columns.str.strip()
    cols_financeiras = ['RO Mês', 'RO Acum', 'Aluguel Mês', '%RO Mês', '%RO Acum', '%Aluguel Mês', 'Multa rescisória atual']
    for col in cols_financeiras:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = (df[col].astype(str)
                           .str.replace('R$', '', regex=False)
                           .str.replace('%', '', regex=False)
                           .str.replace('.', '', regex=False)
                           .str.replace(',', '.', regex=False)
                           .strip())
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
        df_neg = load_data_negativas(arquivo_negativas)
        
        # DASHBOARD DE MÉTRICAS
        total_prejuizo_mes = df_neg['RO Mês'].sum()
        total_prejuizo_acum = df_neg['RO Acum'].sum()
        qtd_lojas = len(df_neg) 
        media_aluguel_perc = df_neg['%Aluguel Mês'].mean()

        c0, c1, c2, c3 = st.columns(4)
        c0.metric("Lojas Analisadas", f"{qtd_lojas}")
        c1.metric("Prejuízo Total Mês", f"R$ {total_prejuizo_mes:,.2f}")
        c2.metric("Prejuízo Acumulado", f"R$ {total_prejuizo_acum:,.2f}")
        c3.metric("Média % Aluguel", f"{media_aluguel_perc:.2f}%")

        # ANÁLISE GRÁFICA
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Top 10 Unidades Críticas (Mês)")
            top_negativas = df_neg.nsmallest(10, 'RO Mês')
            fig_neg = px.bar(top_negativas, x='RO Mês', y='Desc_CC', orientation='h',
                             color='RO Mês', color_continuous_scale='Reds_r')
            fig_neg.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_neg, use_container_width=True)

        with col_graf2:
            st.subheader("Aluguel vs Resultado (Mês)")
            fig_scat = px.scatter(df_neg, x='%Aluguel Mês', y='RO Mês', 
                                  hover_name='Desc_CC', size='Aluguel Mês',
                                  color='Diretor', title="Impacto do Aluguel no RO Mensal")
            fig_scat.update_layout(xaxis_ticksuffix="%")
            st.plotly_chart(fig_scat, use_container_width=True)

        st.markdown("---")
        col_graf3, col_graf4 = st.columns(2)
        with col_graf3:
            st.subheader("Top 10 Unidades Críticas (Acumulado)")
            top_negativas_acum = df_neg.nsmallest(10, 'RO Acum')
            fig_neg_acum = px.bar(top_negativas_acum, x='RO Acum', y='Desc_CC', orientation='h',
                                  color='RO Acum', color_continuous_scale='Reds_r')
            fig_neg_acum.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_neg_acum, use_container_width=True)

        with col_graf4:
            st.subheader("Aluguel vs Resultado (Acumulado)")
            fig_scat_acum = px.scatter(df_neg, x='%Aluguel Mês', y='RO Acum', 
                                       hover_name='Desc_CC', size='Aluguel Mês',
                                       color='Diretor', title="Impacto do Aluguel no RO Acumulado")
            fig_scat_acum.update_layout(xaxis_ticksuffix="%")
            st.plotly_chart(fig_scat_acum, use_container_width=True)

        # RANKINGS DE CUSTO
        st.markdown("---")
        col_rank1, col_rank2 = st.columns(2)
        with col_rank1:
            st.subheader("Top 10 Maiores Aluguéis")
            top_aluguel = df_neg.nlargest(10, 'Aluguel Mês')
            fig_aluguel = px.bar(top_aluguel, x='Aluguel Mês', y='Desc_CC', orientation='h',
                                 color='Aluguel Mês', color_continuous_scale='Blues')
            fig_aluguel.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_aluguel, use_container_width=True)

        with col_rank2:
            st.subheader("Top 10 Maiores Multas")
            if 'Multa rescisória atual' in df_neg.columns:
                top_multa = df_neg.nlargest(10, 'Multa rescisória atual')
                fig_multa = px.bar(top_multa, x='Multa rescisória atual', y='Desc_CC', orientation='h',
                                   color='Multa rescisória atual', color_continuous_scale='Oranges')
                fig_multa.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_multa, use_container_width=True)
            else:
                st.info("Aguardando dados de multa rescisória.")

        # CRUZAMENTO DE DADOS
        st.markdown("---")
        st.subheader("Cruzamento de Dados: Unidades Críticas Recorrentes")
        lojas_mes = set(top_negativas['Desc_CC'])
        lojas_acum = set(top_negativas_acum['Desc_CC'])
        lojas_repetidas = sorted(list(lojas_mes.intersection(lojas_acum)))
        
        if lojas_repetidas:
            st.write(f"Lojas presentes no Top 10 (Mês e Acumulado): {len(lojas_repetidas)}")
            cols = st.columns(len(lojas_repetidas)) 
            for i, loja in enumerate(lojas_repetidas):
                dados_loja = df_neg[df_neg['Desc_CC'] == loja].iloc[0]
                abertura = dados_loja['Inauguração']
                if isinstance(abertura, pd.Timestamp):
                    abertura = abertura.strftime('%d/%m/%Y')
                
                with cols[i]:
                    st.info(f"""
                    **{loja}**
                    - Abertura: {abertura}
                    - RO Mês: R$ {dados_loja['RO Mês']:,.2f}
                    - RO Acum: R$ {dados_loja['RO Acum']:,.2f}
                    - Aluguel: R$ {dados_loja['Aluguel Mês']:,.2f}
                    - Multa: R$ {dados_loja.get('Multa rescisória atual', 0):,.2f}
                    """)
        else:
            st.write("Não há recorrência de lojas entre os rankings selecionados.")

    except Exception as e:
        st.error(f"Erro ao processar lojas negativas: {e}")
else:
    st.info("Faça o upload do arquivo de Lojas Negativas para ativar esta seção.")

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
                    if cmv_para_calculo > 1: 
                        cmv_para_calculo = cmv_para_calculo / 100
                    
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
            r1.info(f"Histórico Positivo: {meses_positivos} meses")
            r2.success(f"Ponto de Equilíbrio CMV {cmv_exibicao_formatado:.0f}%: R$ {p_equilibrio:,.2f}")
            r3.warning(f"Venda Alvo Sugerida CMV 65%: R$ {v_alvo_sugerida:,.2f}")
            st.markdown("---")

        except Exception as e:
            st.error(f"Erro ao processar {arquivo_dre.name}: {e}")

# --- 5. EXPORTAÇÃO PARA PDF ---
st.sidebar.markdown("---")
st.sidebar.header("5. Exportar Relatório")

if st.sidebar.button("Gerar Relatório de Insights PDF"):
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        # Título
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(200, 10, txt="Relatorio Estrategico de Performance", ln=True, align='C')
        pdf.set_font("Arial", size=10)
        pdf.cell(200, 10, txt=f"Gerado em: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='C')
        pdf.ln(10)

        # Insights de Maturação
        if 'df_res' in locals():
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="1. Projecao de Maturacao", ln=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 7, txt=f"Estado Base: {estado_sel}", ln=True)
            pdf.cell(200, 7, txt=f"Venda Alvo: R$ {valor_estudo:,.2f}", ln=True)
            pdf.cell(200, 7, txt=f"Tempo para 100%: {mes_mat} Meses", ln=True)
            pdf.ln(5)

        # Insights de Lojas Negativas
        if 'df_neg' in locals():
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="2. Unidades Negativas", ln=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 7, txt=f"Lojas Analisadas: {qtd_lojas}", ln=True)
            pdf.cell(200, 7, txt=f"Prejuizo Acumulado: R$ {total_prejuizo_acum:,.2f}", ln=True)
            pdf.cell(200, 7, txt=f"Media % Aluguel: {media_aluguel_perc:.2f}%", ln=True)
            
            if 'lojas_repetidas' in locals() and lojas_repetidas:
                pdf.set_font("Arial", 'I', 10)
                pdf.cell(200, 7, txt="Lojas Criticas Recorrentes: " + ", ".join(lojas_repetidas), ln=True)
            pdf.ln(5)

        # Insights DRE
        if 'vals' in locals():
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, txt="3. Analise Financeira (DRE)", ln=True)
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 7, txt=f"Receita Liquida: R$ {vals['RL']:,.2f}", ln=True)
            pdf.cell(200, 7, txt=f"Margem de Contribuicao: R$ {vals['MC']:,.2f}", ln=True)
            pdf.cell(200, 7, txt=f"Resultado Operacional: R$ {vals['RES']:,.2f}", ln=True)
            if 'p_equilibrio' in locals():
                pdf.cell(200, 7, txt=f"Ponto de Equilibrio Calc.: R$ {p_equilibrio:,.2f}", ln=True)
        
        # Gerar binário
        pdf_bin = pdf.output(dest='S').encode('latin-1', 'replace')
        
        st.sidebar.download_button(
            label="📥 Baixar PDF",
            data=pdf_bin,
            file_name=f"Insights_Performance_{datetime.date.today()}.pdf",
            mime="application/pdf"
        )
        st.sidebar.success("PDF preparado com sucesso!")
        
    except Exception as e:
        st.sidebar.error(f"Erro ao gerar relatório: {e}")
