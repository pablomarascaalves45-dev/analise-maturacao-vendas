import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("Projeção de Maturação: Analisador de Dados")
st.markdown("---")

# 2. ENTRADA DE DADOS DE PROJEÇÃO (TAXAS)
st.sidebar.header("Dados de Projeção")
arquivo_subido = st.sidebar.file_uploader(
    "Upload da planilha de Taxas de Crescimento:", 
    type=["xlsx", "xls", "csv"],
    key="proj_file"
)

taxas = [] # Inicializa vazio para evitar erro caso o arquivo não seja carregado
estado_sel = ""

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
                        ano, mes = s_anomes.split('-')[:2]
                    else:
                        ano, mes = s_anomes[:4], s_anomes[4:6]
                    return f"{meses_map[mes]}/{ano[2:]}"
                except: return str(anomes)

            df_loja['Mes_PT'] = df_loja['AnoMes'].apply(formatar_mes_pt)
            df_loja['Valor_Texto'] = df_loja['Mercadoria'].apply(
                lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            )

            fig_hist = px.bar(df_loja, x='Mes_PT', y='Mercadoria', 
                             title=f"Histórico Real vs Projeção de Crescimento - {filial_sel}",
                             labels={'Mercadoria': 'Faturamento Real', 'Mes_PT': 'Período'},
                             template="plotly_white",
                             text='Valor_Texto') 

            fig_hist.add_scatter(x=df_loja['Mes_PT'], y=df_loja['Crescimento_Esperado'], 
                                mode='lines+markers', 
                                name='Projeção Base Estado',
                                line=dict(color='orange', width=3))
            
            fig_hist.update_traces(marker_color='#3366CC', textposition='outside', selector=dict(type='bar'))
            fig_hist.update_layout(yaxis_tickformat="R$,.2f", xaxis_title=None, 
                                   legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
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
        # 1. Localização dinâmica do cabeçalho
        df_raw = pd.read_excel(arquivo_dre, header=None)
        linhas_cab = df_raw[df_raw.iloc[:, 1].astype(str).str.contains("Relato_Linha", na=False)]
        
        if linhas_cab.empty:
            st.error("Erro: Coluna 'Relato_Linha' não encontrada no DRE.")
        else:
            idx_cab = linhas_cab.index[0]
            df_dre_raw = pd.read_excel(arquivo_dre, skiprows=idx_cab)
            df_dre_raw.columns = [str(c).strip() for c in df_dre_raw.columns]

            # 2. Definição de Termos e Busca de Índices
            termos = {
                "RB": "Receita Bruta", "MC": "Margem de Contribuição",
                "PVL": "Perdas Vencidos Liquido", "DISC": "Discrepância _ Estoque",
                "FOLHA": "Despesas Folha", "ADM": "Despesas ADM",
                "OPER": "Despesas Operação", "RES": "Resultado Operacional"
            }

            indices = {}
            for chave, texto in termos.items():
                match = df_dre_raw[df_dre_raw['Relato_Linha'].astype(str).str.contains(texto, case=False, na=False)]
                if not match.empty:
                    indices[chave] = match.index[0]

            # 3. Função de Captura Segura (evita IndexError e lida com colunas duplicadas)
            def pegar_v(chave):
                if chave in indices and "Total" in df_dre_raw.columns:
                    val = df_dre_raw.loc[indices[chave], "Total"]
                    if isinstance(val, pd.Series): # Se houver mais de uma coluna "Total"
                        val = val.iloc[0]
                    return pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0.0
                return 0.0

            vals = {k: pegar_v(k) for k in termos.keys()}

            # 4. Exibição de Métricas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Faturamento", f"R$ {vals['RB']:,.2f}")
            c2.metric("Margem de Contribuição", f"R$ {vals['MC']:,.2f}")
            res_cor = "normal" if vals['RES'] >= 0 else "inverse"
            c3.metric("Resultado Operacional", f"R$ {vals['RES']:,.2f}", delta_color=res_cor)
            perdas_tot = abs(vals['PVL']) + abs(vals['DISC'])
            c4.metric("Perdas/Quebras", f"R$ {perdas_tot:,.2f}")

            # 5. Gráfico de Ofensores
            st.subheader("Análise Operacional")
            col_diag, col_graf = st.columns([1, 1])
            with col_diag:
                if vals['RES'] < 0: st.error(f"Déficit operacional de R$ {abs(vals['RES']):,.2f}.")
                pm = (vals['MC'] / vals['RB'] * 100) if vals['RB'] > 0 else 0
                if pm < 30: st.warning(f"Margem baixa: {pm:.1f}% (Meta 30%).")
                pp = (perdas_tot / vals['RB'] * 100) if vals['RB'] > 0 else 0
                if pp > 1.5: st.warning(f"Quebra alta: {pp:.2f}% (Limite 1.5%).")
            
            with col_graf:
                df_g = pd.DataFrame({
                    "Conta": ["Folha", "ADM", "Operação", "Quebras"],
                    "Valor": [abs(vals['FOLHA']), abs(vals['ADM']), abs(vals['OPER']), perdas_tot]
                })
                fig_p = px.pie(df_g, values='Valor', names='Conta', title="Gastos Operacionais", hole=0.4)
                st.plotly_chart(fig_p, use_container_width=True)

            # 6. Tabela Formatada Dinamicamente
            st.markdown("---")
            st.subheader("Detalhamento Financeiro")
            df_exib = df_dre_raw.dropna(axis=1, how='all').fillna(0)
            
            fmt = {}
            for col in df_exib.columns:
                if any(x in str(col) for x in ["AV-Rl", "%Meta"]): fmt[col] = "{:.2%}"
                elif any(x in str(col) for x in ["Realizado", "Total"]):
                    if pd.api.types.is_numeric_dtype(df_exib[col]): fmt[col] = "{:,.0f}"

            st.dataframe(df_exib.style.format(fmt, na_rep="-"), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erro no processamento do DRE: {e}")
