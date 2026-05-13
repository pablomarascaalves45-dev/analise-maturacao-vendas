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

# 2. SEÇÃO: ENTRADA DE DADOS DE PROJEÇÃO
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

# 3. SEÇÃO: HISTÓRICO REAL
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

# 4. SEÇÃO: ANÁLISE DE NEGATIVAS
st.markdown("---")
st.header("Análise Avançada de Lojas Negativas (Expansão)")
st.sidebar.markdown("---")
st.sidebar.header("3. Análise de Negativas")
arquivo_negativas = st.sidebar.file_uploader("Upload da planilha de Lojas Negativas:", type=["xlsx", "xls", "csv"], key="neg_file")

if arquivo_negativas is not None:
    try:
        df_neg = pd.read_csv(arquivo_negativas, engine='python') if "csv" in arquivo_negativas.name.lower() else pd.read_excel(arquivo_negativas)
        df_neg.columns = [str(c).strip() for c in df_neg.columns]
        
        col_ro_acum = next((c for c in df_neg.columns if 'RO Acum' in c), None)
        col_desc = next((c for c in df_neg.columns if 'Desc_CC' in c), None)
        col_posicao = next((c for c in df_neg.columns if 'Posição Loja' in c), None)
        col_vagas = next((c for c in df_neg.columns if 'Vagas' in c), None)
        col_mercado = next((c for c in df_neg.columns if 'Próximo a mercado' in c), None)
        col_multa = next((c for c in df_neg.columns if 'Multa rescisória atual' in c), None)
        col_cmv_neg = next((c for c in df_neg.columns if 'CMV' in c and 'Acum' in c), None)

        if col_ro_acum and col_desc:
            df_neg[col_ro_acum] = df_neg[col_ro_acum].apply(clean_numeric)
            df_ana = df_neg[df_neg[col_desc].notna()].copy()
            if col_multa: df_ana[col_multa] = df_ana[col_multa].apply(clean_numeric)
            if col_cmv_neg: df_ana[col_cmv_neg] = df_ana[col_cmv_neg].apply(clean_numeric)

            st.subheader("🔍 Diagnóstico de Padrões")
            c1, c2, c3 = st.columns(3)
            with c1:
                if col_posicao:
                    per_pos = df_ana.groupby(col_posicao)[col_ro_acum].mean().sort_values()
                    st.plotly_chart(px.bar(per_pos, orientation='h', title="Posição vs RO Médio"), use_container_width=True)
            with c2:
                if col_vagas:
                    per_vagas = df_ana.groupby(col_vagas)[col_ro_acum].mean().sort_values()
                    st.plotly_chart(px.bar(per_vagas, title="Vagas vs RO Médio"), use_container_width=True)
            with c3:
                if col_mercado:
                    per_mer = df_ana.groupby(col_mercado)[col_ro_acum].mean().sort_values()
                    st.plotly_chart(px.pie(names=per_mer.index, values=abs(per_mer.values), title="Prejuízo Próximo a Mercado?", hole=0.4), use_container_width=True)
            
            st.subheader("📊 Top 15 Lojas com Maior Déficit (Análise RO vs Multa)")
            df_top15 = df_ana.sort_values(by=col_ro_acum).head(15).copy()
            
            st.markdown("""
                <div style="display: flex; gap: 20px; margin-bottom: 10px; font-size: 14px; font-weight: bold;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 15px; height: 15px; background-color: #e8f5e9; border: 1px solid #28a745; border-radius: 4px;"></div>
                        <span style="color: #28a745;">CMV Dentro da Meta (≤ 65%)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 15px; height: 15px; background-color: #fdecea; border: 1px solid #dc3545; border-radius: 4px;"></div>
                        <span style="color: #dc3545;">CMV Acima da Meta (> 65%)</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            if col_cmv_neg:
                cols_baloes = st.columns(len(df_top15))
                for idx, (_, row) in enumerate(df_top15.iterrows()):
                    val_cmv = row[col_cmv_neg]
                    val_exibir = val_cmv if val_cmv > 1 else val_cmv * 100
                    cor_fundo = "#e8f5e9" if val_exibir <= 65 else "#fdecea"
                    cor_texto = "#28a745" if val_exibir <= 65 else "#dc3545"
                    icone = "↑" if val_exibir > 65 else "↓"
                    cols_baloes[idx].markdown(
                        f"""<div style="background-color: {cor_fundo}; color: {cor_texto}; padding: 5px 2px; border-radius: 15px; 
                        text-align: center; font-size: 12px; font-weight: 800; border: 1px solid {cor_texto}; min-height: 35px;">
                        {icone} {val_exibir:.1f}%</div>""", unsafe_allow_html=True
                    )

            fig_top = px.bar(df_top15, x=col_desc, y=col_ro_acum, color=col_ro_acum, color_continuous_scale='Reds_r', text=col_multa if col_multa else None)
            fig_top.update_traces(texttemplate='Multa: R$ %{text:,.2f}' if col_multa else None, textposition='outside', marker_line_width=1.5, opacity=0.9)
            fig_top.update_layout(yaxis_title="RO Acumulado (R$)", xaxis_title=None, coloraxis_showscale=False, height=500, template="plotly_white")
            st.plotly_chart(fig_top, use_container_width=True)

    except Exception as e: st.error(f"Erro em Negativas: {e}")

# 5. SEÇÃO: DRE E RENTABILIDADE
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")
st.sidebar.markdown("---")
st.sidebar.header("4. Dados Financeiros (DRE)")
arquivo_dre = st.sidebar.file_uploader("Upload da planilha de DRE:", type=["xlsx", "xls", "csv"], key="dre_file")

if arquivo_dre is not None:
    try:
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
        c4.metric("Perdas/Discrep.", f"R$ {perdas_totais:,.2f}")
        perc_cmv = (abs(vals['CMV']) / receita_base) * 100
        c5.metric("CMV", f"R$ {abs(vals['CMV']):,.2f}", delta=f"{perc_cmv:.1f}%")

        st.subheader("Análise de Performance Operacional")
        col_diag, col_graf = st.columns([1, 1])
        with col_diag:
            st.write("**Alertas de Indicadores:**")
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
            st.plotly_chart(px.pie(df_gastos, values='Valor', names='Conta', hole=0.4, title="Composição de Gastos"), use_container_width=True)

        st.subheader("Tabela de Dados Financeiros Detalhada")
        df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")
        
        # --- AJUSTE NA LÓGICA DE CONTAGEM SOLICITADA ---
        meses_positivos = 0
        venda_necessaria_idx29 = 0.0
        ponto_equilibrio_idx30 = 0.0
        
        if "RES" in indices:
            row_res = df_dre_raw.iloc[indices["RES"]]
            # Percorre colunas de valores a partir da 3
            for i in range(3, len(row_res)):
                valor_bruto = str(row_res[i]).strip()
                # AJUSTE: Conta apenas se tiver 'R$' no texto e o valor for positivo
                if "R$" in valor_bruto:
                    num_limpo = clean_numeric(valor_bruto)
                    if num_limpo > 0:
                        meses_positivos += 1
            
            if len(row_res) > 30:
                venda_necessaria_idx29 = clean_numeric(row_res[29])
                ponto_equilibrio_idx30 = clean_numeric(row_res[30])

        def estilo_com_realce(row):
            styles = [''] * len(row)
            texto = str(row.iloc[1]).upper()
            if any(c in texto for c in ["RECEITA LÍQUIDA", "MARGEM DE CONTRIBUIÇÃO", "RESULTADO OPERACIONAL"]):
                styles = ['background-color: #f8f9fa; font-weight: bold;'] * len(row)
            if "RESULTADO OPERACIONAL" in texto:
                for i in range(3, len(row)):
                    # Realce visual apenas para quem tem R$ e é positivo
                    val_str = str(row.iloc[i])
                    val_num = clean_numeric(val_str)
                    if "R$" in val_str and val_num > 0:
                        styles[i] = 'background-color: #c8e6c9; font-weight: bold; color: #2e7d32;'
            return styles

        cols_valor = [i for i in range(3, len(df_exibicao.columns), 2)]
        cols_percent = [i for i in range(2, len(df_exibicao.columns), 2)]
        
        def formatar_valor(val, tipo):
            num = clean_numeric(val)
            if num == 0 and (val == "" or val == "-"): return val
            return f"{num:.2f}%" if tipo == "pct" else f"R$ {num:,.2f}"

        df_final = df_exibicao.style.apply(estilo_com_realce, axis=1)
        for col_idx in cols_percent:
            df_final = df_final.format(lambda x: formatar_valor(x, "pct"), subset=pd.IndexSlice[2:, df_exibicao.columns[col_idx]])
        for col_idx in cols_valor:
            df_final = df_final.format(lambda x: formatar_valor(x, "val"), subset=pd.IndexSlice[2:, df_exibicao.columns[col_idx]])

        st.dataframe(df_final, use_container_width=True, hide_index=True)

        st.markdown("### 📋 Relatório de Diagnóstico Financeiro")
        r1, r2, r3 = st.columns(3)
        with r1:
            st.info(f"**Meses no Azul:** {meses_positivos} meses")
        with r2:
            st.success(f"**Venda Necessária (Média):** R$ {venda_necessaria_idx29:,.2f}")
        with r3:
            st.warning(f"**Ponto de Equilíbrio:** R$ {ponto_equilibrio_idx30:,.2f}")
            
        if meses_positivos >= 6:
            st.write("✅ **Análise:** A unidade apresenta consistência operacional positiva no semestre.")
        elif meses_positivos > 0:
            st.write("⚠️ **Análise:** Operação oscilante. Requer atenção ao Ponto de Equilíbrio para estabilização.")
        else:
            st.write("🚨 **Análise:** Unidade em déficit crítico ou sem dados monetários suficientes.")

    except Exception as e: st.error(f"Erro no DRE: {e}")
