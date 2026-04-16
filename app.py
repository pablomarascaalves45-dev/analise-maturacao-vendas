import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("📈 Projeção de Maturação: Analisador de Planilha")
st.markdown("---")

# 2. CAMPO PARA SUBIR O ARQUIVO (PROJEÇÃO)
st.sidebar.header("📁 Dados de Projeção")
arquivo_subido = st.sidebar.file_uploader(
    "Suba a planilha de Taxas de Crescimento:", 
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

        # --- SIDEBAR DE PARÂMETROS ---
        st.sidebar.header("⚙️ Configurações Projeção")
        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Estudo 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        estados_alvo = ["RS", "SC", "PR"]
        colunas_disponiveis = [c for c in df_growth.columns if any(est in str(c) for est in estados_alvo)]
        
        if colunas_disponiveis:
            estado_sel = st.sidebar.selectbox("Escolha o Estado para análise:", estados_alvo)
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

            # --- EXIBIÇÃO DASHBOARD ---
            c1, c2 = st.columns([2, 1])
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                             title=f"Evolução de Faturamento Projetada - {estado_sel} (Início {int(percentual_inicial*100)}%)",
                             template="plotly_white", color_discrete_sequence=["#00CC96"])
                fig.update_layout(xaxis=dict(tickmode='array', tickvals=meses_grafico), yaxis_tickformat="R$,.2f")
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("📊 Marcos de Maturação")
                st.dataframe(df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                            height=450, use_container_width=True, hide_index=True)

            st.markdown("---")
            m1, m12, m2, m3 = st.columns(4)
            m1.metric("Venda Inicial (Mês 1)", f"R$ {projecao[0]:,.2f}", delta=f"{int(percentual_inicial*100)}% do Alvo", delta_color="normal")
            
            v_12 = projecao[11] if len(projecao) >= 12 else 0
            perc_12 = (v_12 / valor_estudo) * 100 if valor_estudo > 0 else 0
            m12.metric("Venda 12 Meses", f"R$ {v_12:,.2f}", delta=f"{perc_12:.1f}% do Alvo", delta_color="normal")
            
            v_final = projecao[-1]
            perc_final = (v_final / valor_estudo) * 100 if valor_estudo > 0 else 0
            m2.metric("Venda Final (Mês 36)", f"R$ {v_final:,.2f}", delta=f"{perc_final:.1f}% do Alvo", delta_color="normal")
            
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Acima de 36m"
            m3.metric("Maturação (100%)", f"Mês {mes_mat}")

        else:
            st.warning("⚠️ Estados RS, SC ou PR não detectados.")
    except Exception as e:
        st.error(f"Erro Projeção: {e}")

# --- SEÇÃO: HISTÓRICO REAL 12 MESES (CONFORME SOLICITADO) ---
st.markdown("### 🏪 Histórico Real vs Crescimento Esperado")
st.sidebar.markdown("---")
st.sidebar.header("📁 Dados Históricos")
arquivo_historico = st.sidebar.file_uploader(
    "Suba a planilha de Vendas Realizadas (12 Meses):", 
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
            filial_sel = st.selectbox("Selecione a Filial para ver o Histórico Real:", filiais)
            
            df_loja = df_hist[df_hist['Desc_Filial'] == filial_sel].copy()
            df_loja = df_loja.sort_values(by='AnoMes')

            venda_inicial_real = df_loja['Mercadoria'].iloc[0]
            esperado = [venda_inicial_real]
            
            for i in range(1, len(df_loja)):
                if i < len(taxas):
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
                    if '-' in str(anomes):
                        ano, mes = str(anomes).split('-')
                    else:
                        ano, mes = str(anomes)[:4], str(anomes)[4:]
                    return f"{meses_map[mes]}/{ano[2:]}"
                except: return str(anomes)

            df_loja['Mes_PT'] = df_loja['AnoMes'].apply(formatar_mes_pt)
            df_loja['Valor_Texto'] = df_loja['Mercadoria'].apply(
                lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            )

            fig_hist = px.bar(df_loja, x='Mes_PT', y='Mercadoria', 
                             title=f"Histórico Real vs Projeção de Crescimento do Estado ({estado_sel}) - {filial_sel}",
                             labels={'Mercadoria': 'Faturamento Real', 'Mes_PT': 'Mês'},
                             template="plotly_white",
                             text='Valor_Texto') 

            fig_hist.add_scatter(x=df_loja['Mes_PT'], y=df_loja['Crescimento_Esperado'], 
                                mode='lines+markers', 
                                name='Crescimento Esperado (Estado)',
                                line=dict(color='orange', width=3))
            
            fig_hist.update_traces(marker_color='#3366CC', textposition='outside', selector=dict(type='bar'))
            
            fig_hist.update_layout(
                yaxis_tickformat="R$,.2f",
                xaxis_title=None,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
            
            with st.expander("Ver comparação de valores (Real vs Esperado)"):
                df_comp = df_loja[['Mes_PT', 'Mercadoria', 'Crescimento_Esperado']].copy()
                df_comp.columns = ['Mês', 'Real (R$)', 'Esperado (R$)']
                st.dataframe(df_comp.style.format({'Real (R$)': 'R$ {:,.2f}', 'Esperado (R$)': 'R$ {:,.2f}'}), use_container_width=True)
        else:
            st.error("A planilha de histórico deve conter a coluna 'Desc_Filial'.")
            
    except Exception as e:
        st.error(f"Erro ao processar histórico: {e}")

# --- NOVA SEÇÃO: ANALISADOR DE DRE (CORRIGIDO PARA EVITAR KEYERROR) ---
st.markdown("---")
st.header("📋 Analisador de DRE: Diagnóstico de Rentabilidade")

st.sidebar.markdown("---")
st.sidebar.header("📁 Dados Financeiros (DRE)")
arquivo_dre = st.sidebar.file_uploader(
    "Suba a planilha de DRE (Excel/CSV):", 
    type=["xlsx", "xls", "csv"],
    key="dre_file"
)

if arquivo_dre is not None:
    try:
        # Leitura da DRE
        if "csv" in arquivo_dre.name.lower():
            df_dre = pd.read_csv(arquivo_dre, engine='python')
        else:
            df_dre = pd.read_excel(arquivo_dre)

        # Limpeza de nomes de colunas para evitar erros de espaços
        df_dre.columns = [str(c).strip() for c in df_dre.columns]

        # Função para buscar valor de forma segura
        def get_metric(keyword):
            # Procura a palavra-chave na coluna que contém as descrições (geralmente a segunda coluna útil)
            mask = df_dre.apply(lambda row: row.astype(str).str.contains(keyword, case=False).any(), axis=1)
            row = df_dre[mask]
            if not row.empty:
                # Busca o valor na coluna 'Realizado' ou 'Total'
                for col in ['Realizado', 'Total', 'Valor']:
                    if col in df_dre.columns:
                        return pd.to_numeric(row[col].iloc[0], errors='coerce')
                # Se não achar colunas nomeadas, pega a última coluna numérica
                return pd.to_numeric(row.iloc[0, -1], errors='coerce')
            return 0.0

        receita = get_metric("Receita Bruta")
        margem = get_metric("Margem de Contribuição")
        despesas = get_metric("Despesas Operação")
        resultado = get_metric("Lucro/Prejuízo")

        # Layout de métricas
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Faturamento", f"R$ {receita:,.2f}")
        d2.metric("Margem", f"R$ {margem:,.2f}")
        d3.metric("Despesas", f"R$ {abs(despesas):,.2f}", delta_color="inverse")
        d4.metric("Resultado Líquido", f"R$ {resultado:,.2f}", delta_color="normal" if resultado >= 0 else "inverse")

        # Diagnóstico Inteligente
        st.subheader("🕵️ Diagnóstico de Performance")
        
        with st.expander("Clique para ver o relatório detalhado", expanded=True):
            if resultado < 0:
                st.error(f"🚨 **A operação está negativa em R$ {abs(resultado):,.2f}**")
                
                # Lógica de análise
                if receita > 0:
                    perc_despesa = (abs(despesas) / receita) * 100
                    if perc_despesa > 25:
                        st.warning(f"⚠️ **Despesas Operacionais críticas:** Estão consumindo {perc_despesa:.1f}% do faturamento. O ideal para o setor é abaixo de 20%.")
                    
                    perc_margem = (margem / receita) * 100
                    if perc_margem < 30:
                        st.warning(f"📉 **Margem de Contribuição baixa:** {perc_margem:.1f}%. Verifique quebra de estoque ou excesso de descontos.")
            else:
                st.success("✅ A unidade apresenta resultado operacional positivo.")

        # Identificação de Despesas Críticas para o Gráfico
        # Filtra linhas que contenham valores negativos na coluna de resultado
        df_filt = df_dre.copy()
        if 'Realizado' in df_filt.columns:
            # Pega as 5 maiores despesas (valores negativos)
            top_despesas = df_filt[pd.to_numeric(df_filt['Realizado'], errors='coerce') < 0].sort_values(by='Realizado').head(5)
            
            if not top_despesas.empty:
                st.write("**⚠️ Principais Ofensores (Maiores Gastos):**")
                # Usa a primeira coluna de texto como nome da despesa
                col_nome = top_despesas.columns[1] 
                top_despesas['Valor_Abs'] = top_despesas['Realizado'].abs()
                
                fig_dre = px.bar(top_despesas, x=col_nome, y='Valor_Abs', 
                                 title="Maiores Despesas Identificadas",
                                 labels={'Valor_Abs': 'Valor (R$)', col_nome: 'Conta'},
                                 color_discrete_sequence=['#EF553B'])
                st.plotly_chart(fig_dre, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao analisar DRE: Certifique-se de que a planilha subida é a DRE padrão.")
        st.info(f"Detalhe técnico: {e}")
