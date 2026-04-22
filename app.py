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
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("Marcos de Maturação")
                st.dataframe(df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                            height=450, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erro na Projeção: {e}")

# --- SEÇÃO: HISTÓRICO REAL ---
st.markdown("### Histórico Real vs Crescimento Projetado")
arquivo_historico = st.sidebar.file_uploader("Upload Histórico (12 Meses):", type=["xlsx", "xls", "csv"], key="hist_file")

if arquivo_historico is not None:
    try:
        df_hist = pd.read_excel(arquivo_historico) if "xls" in arquivo_historico.name else pd.read_csv(arquivo_historico)
        if 'Desc_Filial' in df_hist.columns:
            filial_sel = st.selectbox("Unidade:", sorted(df_hist['Desc_Filial'].unique()))
            df_loja = df_hist[df_hist['Desc_Filial'] == filial_sel].sort_values(by='AnoMes')
            st.write(f"Análise para: {filial_sel}")
            # Lógica de gráfico aqui (omitida para brevidade, mantendo foco no DRE)
    except Exception as e:
        st.error(f"Erro Histórico: {e}")

# --- SEÇÃO DRE ---
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")

arquivo_dre = st.sidebar.file_uploader("Upload da planilha de DRE:", type=["xlsx", "xls", "csv"], key="dre_file")

if arquivo_dre is not None:
    try:
        df_dre_raw = pd.read_excel(arquivo_dre, header=None)
        
        # Identificação de índices para Métricas
        termos = {"RB": "Receita Bruta", "MC": "Margem de Contribuição", "RES": "Resultado Operacional"}
        vals = {}
        for chave, texto in termos.items():
            match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.contains(texto, case=False, na=False)]
            vals[chave] = pd.to_numeric(df_dre_raw.iloc[match.index[0], 3], errors='coerce') if not match.empty else 0.0

        c1, c2, c3 = st.columns(3)
        c1.metric("Faturamento", f"R$ {vals['RB']:,.2f}")
        c2.metric("Margem", f"R$ {vals['MC']:,.2f}")
        c3.metric("Resultado", f"R$ {vals['RES']:,.2f}")

        # --- TABELA DETALHADA ---
        st.markdown("---")
        st.subheader("Tabela de Dados Financeiros Detalhada")
        
        df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")

        # Identificação dinâmica de colunas baseada na Linha 3 (índice 2)
        colunas_avri = []
        colunas_realizado = []
        
        if len(df_exibicao) > 2:
            linha_cabecalho = df_exibicao.iloc[2].astype(str).str.upper()
            for i in range(len(df_exibicao.columns)):
                texto = linha_cabecalho.iloc[i]
                if "AV-RI" in texto or "AV-RL" in texto:
                    colunas_avri.append(df_exibicao.columns[i])
                elif "REALIZADO" in texto:
                    colunas_realizado.append(df_exibicao.columns[i])

        # Formatador para Porcentagem (Coluna 2 + Colunas AV-RI)
        def formatador_porcentagem(val):
            try:
                if isinstance(val, str) and any(x in val.upper() for x in ["AV-RI", "AV-RL", "META"]):
                    return val
                num = pd.to_numeric(val, errors='coerce')
                if pd.notnull(num) and num != "":
                    return f"{float(num) * 100:.2f}%".replace('.', ',')
                return val
            except:
                return val

        # Formatador para Inteiros (Colunas Realizado)
        def formatador_inteiro(val):
            try:
                if isinstance(val, str) and "REALIZADO" in val.upper():
                    return val
                num = pd.to_numeric(val, errors='coerce')
                if pd.notnull(num) and num != "":
                    return f"{int(round(float(num))):,}".replace(',', '.')
                return val
            except:
                return val

        # Aplicar estilos
        col_pct = list(set([2] + colunas_avri)) # Coluna 2 fixo + dinâmicas
        
        st.dataframe(
            df_exibicao.style.format(subset=col_pct, formatter=formatador_porcentagem)
                             .format(subset=colunas_realizado, formatter=formatador_inteiro), 
            use_container_width=True, 
            hide_index=True
        )

    except Exception as e:
        st.error(f"Erro no processamento do DRE: {e}")
