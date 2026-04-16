import pandas as pd
import plotly.express as px
import streamlit as st

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("📈 Projeção de Maturação: Upload de Planilha")
st.markdown("---")

# 2. CAMPO PARA SUBIR O ARQUIVO
st.sidebar.header("📁 Importar Dados")
arquivo_subido = st.sidebar.file_uploader(
    "Suba sua planilha (Excel ou CSV):", 
    type=["xlsx", "xls", "csv"]
)

if arquivo_subido is not None:
    try:
        # Identifica se é Excel ou CSV e lê corretamente
        if arquivo_subido.name.endswith('.csv'):
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)

        # --- SIDEBAR DE PARÂMETROS ---
        st.sidebar.header("⚙️ Configurações")
        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Estudo 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        # Identifica colunas (RS, SC, PR)
        colunas_disponiveis = [c for c in df_growth.columns if c in ["RS", "SC", "PR"]]
        estados = list(dict.fromkeys(colunas_disponiveis))
        
        if estados:
            estado_sel = st.sidebar.selectbox("Escolha o Estado:", estados)
            
            # --- CÁLCULO DA CURVA ---
            col_dados = df_growth[estado_sel]
            # Se houver duplicadas, pega a coluna de taxas (geralmente a última)
            if isinstance(col_dados, pd.DataFrame):
                taxas = pd.to_numeric(col_dados.iloc[:, -1], errors='coerce').fillna(0).values
            else:
                taxas = pd.to_numeric(col_dados, errors='coerce').fillna(0).values

            projecao = []
            valor_atual = valor_estudo * 0.6 # Mês 1 = 60%
            projecao.append(valor_atual)
            
            # Cálculo dos 36 meses
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

            # --- DASHBOARD ---
            c1, c2 = st.columns([2, 1])
            
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                             title=f"Curva de Maturação - {estado_sel}",
                             template="plotly_white")
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("📊 Tabela de Evolução")
                st.dataframe(
                    df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                    height=450, use_container_width=True
                )

            # MÉTRICAS
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Venda Inicial", f"R$ {projecao[0]:,.2f}")
            m2.metric("Venda Mês 36", f"R$ {projecao[-1]:,.2f}")
            
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "N/A"
            m3.metric("Mês Maturação (100%)", f"Mês {mes_mat}")

        else:
            st.warning("⚠️ Nenhuma coluna RS, SC ou PR encontrada nesta planilha.")
            
    except Exception as e:
        st.error(f"Erro ao ler o arquivo: {e}")
else:
    st.info("👋 Aguardando upload... Por favor, suba um arquivo Excel ou CSV na barra lateral.")
