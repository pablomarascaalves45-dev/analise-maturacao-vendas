import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação & Expansão", layout="wide")

st.title("Projeção de Maturação e Análise de Performance")
st.markdown("---")

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


# --- NOVA SEÇÃO: ANÁLISE DE LOJAS NEGATIVAS (EXPANSÃO) ---
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
        # Carregamento tratando vírgulas como decimais para o arquivo de expansão
        if "csv" in arquivo_negativas.name.lower():
            df_neg = pd.read_csv(arquivo_negativas, decimal=',', engine='python')
        else:
            df_neg = pd.read_excel(arquivo_negativas)

        # Limpeza básica: remove linhas onde o Código da Unidade ou Resultado Acumulado são nulos
        df_neg = df_neg.dropna(subset=['Cod Unidade', 'RO Acum'])

        # Métricas Consolidadas
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
            # Pareto de Prejuízo
            df_neg_sorted = df_neg.sort_values(by='RO Acum', ascending=True).head(12)
            fig_ofensores = px.bar(df_neg_sorted, x='Desc_CC', y='RO Acum', 
                                  title="Unidades com Maior Prejuízo Acumulado",
                                  color='RO Acum', color_continuous_scale='Reds_r',
                                  labels={'RO Acum': 'Resultado Acum.', 'Desc_CC': 'Loja'})
            st.plotly_chart(fig_ofensores, use_container_width=True)

        with t2:
            # Correlação Aluguel vs Margem
            fig_corr = px.scatter(df_neg, x='%Aluguel Mês', y='%RO Mês', 
                                 size='Aluguel Mês', hover_name='Desc_CC', color='Diretor',
                                 title="Peso do Aluguel vs Margem Operacional (%)",
                                 trendline="ols")
            st.plotly_chart(fig_corr, use_container_width=True)
            st.info("💡 Lojas no quadrante inferior direito indicam aluguel alto consumindo a pouca margem gerada.")

        with t3:
            # Análise por Posição de Loja (Esquina vs Meio)
            df_pos = df_neg.groupby('Posição Loja')['RO Acum'].mean().reset_index()
            fig_pos = px.pie(df_pos, values=df_pos['RO Acum'].abs(), names='Posição Loja', 
                            title="Impacto Médio no Prejuízo por Posição de Imóvel",
                            color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pos, use_container_width=True)

        # Painel de Alertas Automáticos
        st.markdown("#### 🔍 Insights de Negócios")
        col_ins1, col_ins2 = st.columns(2)
        
        with col_ins1:
            # Lojas com aluguel crítico
            criticas = df_neg[df_neg['%Aluguel Mês'] > 0.10]['Desc_CC'].unique()
            st.error(f"**Aluguel Crítico (>10% da Venda):** {len(criticas)} lojas.")
            if len(criticas) > 0:
                st.caption(", ".join(criticas))
        
        with col_ins2:
            # Analise de Diretores
            pior_diretoria = df_neg.groupby('Diretor')['RO Acum'].sum().idxmin()
            st.warning(f"**Diretoria com Maior Déficit:** {pior_diretoria}")

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
            "RB": "Receita Bruta",
            "RL": "Receita Líquida",
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
        receita_base = vals['RL'] if vals['RL'] > 0 else vals['RB']

        match_cmv = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains("CMV", case=False, na=False)]
        cmv_total = 0.0
        if not match_cmv.empty:
            val_cmv = df_dre_raw.iloc[match_cmv.index[0], 3]
            cmv_total = pd.to_numeric(val_cmv, errors='coerce') if pd.notnull(val_cmv) else 0.0

        c1, c2, c3, c4, c5 = st.columns(5) 
        c1.metric("Receita Líquida", f"R$ {vals['RL']:,.2f}")
        c2.metric("Margem de Contribuição", f"R$ {vals['MC']:,.2f}")
        
        res_cor = "normal" if vals['RES'] >= 0 else "inverse"
        c3.metric("Resultado Operacional", f"R$ {vals['RES']:,.2f}", delta_color=res_cor)
        
        perdas_totais = abs(vals['PVL']) + abs(vals['DISC'])
        c4.metric("Perdas e Discrepâncias", f"R$ {perdas_totais:,.2f}")

        perc_cmv = (abs(cmv_total) / receita_base * 100) if receita_base > 0 else 0
        cor_cmv = "inverse" if perc_cmv > 65 else "normal"
        c5.metric("CMV", f"R$ {cmv_total:,.2f}", delta=f"{perc_cmv:.2f}%", delta_color=cor_cmv)

        perc_folha = (abs(vals['FOLHA']) / receita_base * 100) if receita_base > 0 else 0
        perc_adm = (abs(vals['ADM']) / receita_base * 100) if receita_base > 0 else 0
        perc_oper = (abs(vals['OPER']) / receita_base * 100) if receita_base > 0 else 0
        perc_perda = (perdas_totais / receita_base * 100) if receita_base > 0 else 0
        perc_margem = (vals['MC'] / receita_base * 100) if receita_base > 0 else 0

        st.subheader("Análise de Performance Operacional")
        col_diag, col_graf = st.columns([1, 1])
        
        with col_diag:
            st.write("Alertas de Indicadores (Base: Receita Líquida):")
            if vals['RES'] < 0:
                st.error(f"Resultado Negativo: Déficit operacional de R$ {abs(vals['RES']):,.2f}.")
            if perc_margem < 35:
                st.warning(f"Margem Abaixo da Meta ({perc_margem:.2f}%): A meta é 35%.")
            if perc_perda > 1.5:
                st.warning(f"Nível de Quebra Elevado ({perc_perda:.2f}%): A meta é 0,66%.")

        with col_graf:
            df_gastos = pd.DataFrame({
                "Conta": ["Folha", "ADM", "Operação", "Quebra/Perdas"],
                "Valor": [abs(vals['FOLHA']), abs(vals['ADM']), abs(vals['OPER']), perdas_totais]
            }).sort_values(by="Valor", ascending=False)
            
            fig_ofensores = px.pie(df_gastos, values='Valor', names='Conta', 
                                   title="Composição de Gastos Operacionais",
                                   color_discrete_sequence=px.colors.sequential.RdBu)
            fig_ofensores.update_traces(textinfo='percent+label')
            st.plotly_chart(fig_ofensores, use_container_width=True)

        st.markdown("---")
        st.subheader("Tabela de Dados Financeiros Detalhada")
        
        df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")
        df_exibicao.insert(0, 'Nº', range(1, len(df_exibicao) + 1))

        colunas_avri = []
        colunas_realizado = []
        for col_idx in range(len(df_exibicao.columns)):
            cabecalho_texto = df_exibicao.iloc[0:4, col_idx].astype(str).str.upper()
            if cabecalho_texto.str.contains("AV-RI").any() or cabecalho_texto.str.contains("AV-RL").any():
                colunas_avri.append(df_exibicao.columns[col_idx])
            if cabecalho_texto.str.contains("REALIZADO").any():
                colunas_realizado.append(df_exibicao.columns[col_idx])

        def formatador_porcentagem(val):
            if val == "" or val == "-" or val == " ": return val
            try:
                num = float(str(val).replace(',', '.'))
                return f"{num * 100:.2f}%".replace('.', ',')
            except: return val

        def formatador_decimal(val):
            if val == "" or val == "-" or val == " ": return val
            try:
                num = float(str(val).replace(',', '.'))
                return f"{num:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            except: return val

        contas_destaque = [
            "Receita Bruta", "Deduções", "Receita Líquida", "CMV", 
            "Perdas Vencidos Liquido", "Discrepância _ Estoque", 
            "Margem de Contribuição", "Despesas Folha", "Despesas ADM", 
            "Despesas Operação", "Resultado Operacional"
        ]

        def estilo_linhas_mestre(row):
            texto_celula = str(row.iloc[2]).strip() 
            if any(conta.lower() in texto_celula.lower() for conta in contas_destaque):
                return ['background-color: #f0f7ff; font-weight: bold; border-bottom: 1.5px solid #d1dbe5;'] * len(row)
            return [''] * len(row)

        col_pct_alvo = list(set([3] + colunas_avri))
        
        df_estilizado = (
            df_exibicao.style
            .apply(estilo_linhas_mestre, axis=1)
            .format(subset=col_pct_alvo, formatter=formatador_porcentagem)
            .format(subset=colunas_realizado, formatter=formatador_decimal)
        )

        st.dataframe(df_estilizado, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erro no processamento do DRE: {e}")
