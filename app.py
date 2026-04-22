import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("Projeção de Maturação: Analisador de Dados")
st.markdown("---")

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
            
            # Tratamento de Porcentagem robusto
            def limpar_porcentagem(val):
                if isinstance(val, str):
                    val = val.replace('%', '').replace(',', '.')
                return pd.to_numeric(val, errors='coerce')

            raw_taxas = df_growth[col_nome_real].apply(limpar_porcentagem).fillna(0).values
            taxas = [t/100 if abs(t) > 1 else t for t in raw_taxas]

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

            # --- DASHBOARD ---
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

    except Exception as e:
        st.error(f"Erro na Projeção: {e}")

# --- SEÇÃO DRE CORRIGIDA ---
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")

arquivo_dre = st.sidebar.file_uploader(
    "Upload da planilha de DRE:", 
    type=["xlsx", "xls", "csv"],
    key="dre_file"
)

if arquivo_dre is not None:
    try:
        df_raw = pd.read_excel(arquivo_dre, header=None)
        
        # Localiza cabeçalho real
        linhas_cab = df_raw[df_raw.iloc[:, 1].astype(str).str.contains("Relato_Linha", na=False)]
        if not linhas_cab.empty:
            idx_cab = linhas_cab.index[0]
            df_dre_raw = pd.read_excel(arquivo_dre, skiprows=idx_cab)
            df_dre_raw.columns = [str(c).strip() for c in df_dre_raw.columns]

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

            def pegar_v(chave):
                if chave in indices:
                    # Tenta pegar a coluna 'Total' ou 'Realizado'
                    col_valor = "Total" if "Total" in df_dre_raw.columns else "Realizado"
                    if col_valor in df_dre_raw.columns:
                        val = df_dre_raw.loc[indices[chave], col_valor]
                        if isinstance(val, pd.Series): val = val.iloc[0]
                        return pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0.0
                return 0.0

            vals = {k: pegar_v(k) for k in termos.keys()}

            # Métricas
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Faturamento", f"R$ {vals['RB']:,.2f}")
            c2.metric("Margem de Contribuição", f"R$ {vals['MC']:,.2f}")
            res_cor = "normal" if vals['RES'] >= 0 else "inverse"
            c3.metric("Resultado Operacional", f"R$ {vals['RES']:,.2f}", delta_color=res_cor)
            perdas_tot = abs(vals['PVL']) + abs(vals['DISC'])
            c4.metric("Perdas/Quebras", f"R$ {perdas_tot:,.2f}")

            # --- CORREÇÃO DA TABELA DETALHADA ---
            st.markdown("---")
            st.subheader("Tabela de Dados Financeiros Detalhada")
            df_exib = df_dre_raw.dropna(axis=1, how='all').fillna(0)
            
            # Formatação Dinâmica Segura
            fmt = {}
            for col in df_exib.columns:
                # Só aplica formato numérico se a coluna for do tipo float ou int
                is_numeric = pd.api.types.is_numeric_dtype(df_exib[col])
                
                if is_numeric:
                    if any(x in str(col) for x in ["AV-RI", "AV-Rl", "%", "Meta"]):
                        fmt[col] = "{:.2%}"
                    elif any(x in str(col) for x in ["Realizado", "Total", "2025"]):
                        fmt[col] = "{:,.0f}"

            st.dataframe(df_exib.style.format(fmt, na_rep="-"), use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erro no processamento do DRE: {e}")
