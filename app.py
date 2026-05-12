import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("Projeção de Maturação: Analisador de Dados")
st.markdown("---")

# Função auxiliar para limpeza numérica
def clean_numeric(val):
    if pd.isna(val) or val == "" or val == "-":
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

# 2. ENTRADA DE DADOS DE PROJEÇÃO
st.sidebar.header("Dados de Projeção")
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
            meses_map = {'01':'Jan','02':'Fev','03':'Mar','04':'Abr','05':'Mai','06':'Jun','07':'Jul','08':'Ago','09':'Set','10':'Out','11':'Nov','12':'Dez'}
            def formatar_mes_pt(anomes):
                try:
                    s_anomes = str(anomes)
                    ano, mes = (s_anomes.split('-') if '-' in s_anomes else (s_anomes[:4], s_anomes[4:]))
                    return f"{meses_map[mes]}/{ano[2:]}"
                except: return str(anomes)
            df_loja['Mes_PT'] = df_loja['AnoMes'].apply(formatar_mes_pt)
            df_loja['Valor_Texto'] = df_loja['Mercadoria'].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
            fig_hist = px.bar(df_loja, x='Mes_PT', y='Mercadoria', title=f"Histórico Real vs Projeção ({filial_sel})", template="plotly_white", text='Valor_Texto') 
            fig_hist.add_scatter(x=df_loja['Mes_PT'], y=df_loja['Crescimento_Esperado'], mode='lines+markers', name='Projeção Base Estado', line=dict(color='orange', width=3))
            fig_hist.update_traces(marker_color='#3366CC', textposition='outside', selector=dict(type='bar'))
            st.plotly_chart(fig_hist, use_container_width=True)
    except Exception as e:
        st.error(f"Erro no histórico: {e}")

# --- NOVA SEÇÃO: ANÁLISE DE EXPANSÃO (NEGATIVAS) ---
st.markdown("---")
st.header("Análise Avançada de Lojas Negativas (Expansão)")

st.sidebar.markdown("---")
st.sidebar.header("Análise de Negativas")
arquivo_negativas = st.sidebar.file_uploader(
    "Upload da planilha de Lojas Negativas:", 
    type=["xlsx", "xls", "csv"],
    key="neg_file"
)

if arquivo_negativas is not None:
    try:
        df_neg = pd.read_csv(arquivo_negativas, engine='python') if "csv" in arquivo_negativas.name.lower() else pd.read_excel(arquivo_negativas)
        df_neg.columns = [str(c).strip() for c in df_neg.columns]
        
        # Mapeamento Dinâmico
        col_ro_acum = next((c for c in df_neg.columns if 'RO Acum' in c), None)
        col_desc = next((c for c in df_neg.columns if 'Desc_CC' in c), None)
        col_aluguel_perc = next((c for c in df_neg.columns if '%Aluguel' in c), None)
        col_vagas = next((c for c in df_neg.columns if 'Vagas' in c), None)
        col_posicao = next((c for c in df_neg.columns if 'Posição Loja' in c), None)
        col_mercado = next((c for c in df_neg.columns if 'Próximo a mercado' in c), None)

        if col_ro_acum and col_desc:
            # Tratamento
            df_neg[col_ro_acum] = df_neg[col_ro_acum].apply(clean_numeric)
            if col_aluguel_perc: df_neg[col_aluguel_perc] = df_neg[col_aluguel_perc].apply(clean_numeric)
            
            df_ana = df_neg[df_neg[col_desc].notna()].copy()
            
            # Painel de Insights
            st.subheader("🔍 Diagnóstico de Padrões")
            c1, c2, c3 = st.columns(3)
            
            with c1:
                if col_posicao:
                    per_pos = df_ana.groupby(col_posicao)[col_ro_acum].mean().sort_values()
                    fig_pos = px.bar(per_pos, orientation='h', title="Impacto: Posição da Loja (Média RO)", color_continuous_scale='Reds')
                    st.plotly_chart(fig_pos, use_container_width=True)
            
            with c2:
                if col_vagas:
                    per_vagas = df_ana.groupby(col_vagas)[col_ro_acum].mean().sort_values()
                    fig_vagas = px.bar(per_vagas, title="Impacto: Disponibilidade de Vagas", color_discrete_sequence=['#FFA15A'])
                    st.plotly_chart(fig_vagas, use_container_width=True)

            with c3:
                if col_mercado:
                    per_mer = df_ana.groupby(col_mercado)[col_ro_acum].mean().sort_values()
                    fig_mer = px.pie(names=per_mer.index, values=abs(per_mer.values), title="Prejuízo: Próximo a Mercado?")
                    st.plotly_chart(fig_mer, use_container_width=True)

            # Análise de Ofensores
            st.subheader("📊 Top 15 Lojas com Maior Déficit Acumulado")
            df_top_neg = df_ana.sort_values(by=col_ro_acum).head(15)
            fig_ofensores = px.bar(df_top_neg, x=col_desc, y=col_ro_acum, color=col_ro_acum,
                                   hover_data=[col_aluguel_perc] if col_aluguel_perc else [],
                                   color_continuous_scale='Reds_r', text_auto='.2s')
            st.plotly_chart(fig_ofensores, use_container_width=True)

            # Tabela de Dados com Filtro
            st.subheader("📋 Matriz de Dados Completa")
            st.dataframe(df_ana.style.background_gradient(subset=[col_ro_acum], cmap='Reds_r'), use_container_width=True)
        else:
            st.warning("Colunas essenciais não detectadas no arquivo de Negativas.")
    except Exception as e:
        st.error(f"Erro na análise de Negativas: {e}")

# --- SEÇÃO DRE (Estrutura Mantida) ---
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")
st.sidebar.markdown("---")
st.sidebar.header("Dados Financeiros (DRE)")
arquivo_dre = st.sidebar.file_uploader("Upload da planilha de DRE:", type=["xlsx", "xls", "csv"], key="dre_file")

if arquivo_dre is not None:
    try:
        df_dre_raw = pd.read_excel(arquivo_dre, header=None)
        termos = {"RB": "Receita Bruta", "RL": "Receita Líquida", "MC": "Margem de Contribuição", "PVL": "Perdas Vencidos Liquido", "DISC": "Discrepância _ Estoque", "FOLHA": "Despesas Folha", "ADM": "Despesas ADM", "OPER": "Despesas Operação", "RES": "Resultado Operacional"}
        indices = {}
        for chave, texto in termos.items():
            match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains(texto, case=False, na=False)]
            if not match.empty: indices[chave] = match.index[0]
        def pegar_v(chave):
            if chave in indices:
                val = df_dre_raw.iloc[indices[chave], 3] 
                return pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0.0
            return 0.0
        vals = {k: pegar_v(k) for k in termos.keys()}
        receita_base = vals['RL'] if vals['RL'] > 0 else vals['RB']
        
        c1, c2, c3, c4 = st.columns(4) 
        c1.metric("Receita Líquida", f"R$ {vals['RL']:,.2f}")
        c2.metric("Margem Contrib.", f"R$ {vals['MC']:,.2f}")
        c3.metric("Resultado Oper.", f"R$ {vals['RES']:,.2f}", delta_color="normal" if vals['RES'] >= 0 else "inverse")
        c4.metric("Perdas/Discrep.", f"R$ {(abs(vals['PVL']) + abs(vals['DISC'])):,.2f}")

        st.dataframe(df_dre_raw.dropna(axis=1, how='all').fillna(""), use_container_width=True)
    except Exception as e:
        st.error(f"Erro no DRE: {e}")
