import pandas as pd
import plotly.express as px
import streamlit as st
import os

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("📈 Projeção de Crescimento de Vendas")
st.markdown("---")

# 2. CAMINHO DO ARQUIVO (NOME EXATO QUE ESTÁ NO SEU GITHUB)
NOME_ARQUIVO = "crescimento.csv.xlsx"

def carregar_dados():
    if os.path.exists(NOME_ARQUIVO):
        # Lendo com decimal=',' por causa do formato da planilha brasileira
        return pd.read_csv(NOME_ARQUIVO, decimal=',', engine='python')
    return None

df_growth = carregar_dados()

if df_growth is not None:
    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Configurações")
    valor_estudo = st.sidebar.number_input("Valor de Estudo (100%):", min_value=0.0, value=400000.0, step=10000.0)
    
    # Identifica colunas RS, SC, PR
    cols_validas = [c for c in df_growth.columns if c in ["RS", "SC", "PR"]]
    estados = list(dict.fromkeys(cols_validas)) # Remove duplicatas de nome
    
    estado_sel = st.sidebar.selectbox("Escolha o Estado:", estados)
    
    st.sidebar.markdown("---")
    st.sidebar.info(f"💡 **Mês 1:** R$ {valor_estudo * 0.6:,.2f} (60%)")

    # --- CÁLCULO DA MATURAÇÃO ---
    # Pegamos a coluna do estado. Se houver duplicada, pegamos a que contém os dados de taxa
    col_dados = df_growth[estado_sel]
    if isinstance(col_dados, pd.DataFrame):
        # Seleciona a coluna que tem as variações (geralmente a segunda ocorrência no seu CSV)
        taxas = pd.to_numeric(col_dados.iloc[:, -1], errors='coerce').fillna(0).values
    else:
        taxas = pd.to_numeric(col_dados, errors='coerce').fillna(0).values

    projecao = []
    # Mês 1: 60% do valor de estudo
    venda_atual = valor_estudo * 0.6
    projecao.append(venda_atual)
    
    # Mês 2 ao 36
    for i in range(1, 36):
        if i < len(taxas):
            taxa_mes = taxas[i]
            venda_atual = venda_atual * (1 + taxa_mes)
            projecao.append(venda_atual)
    
    df_res = pd.DataFrame({
        "Mês": range(1, len(projecao) + 1),
        "Faturamento": projecao
    })
    df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100

    # --- VISUALIZAÇÃO ---
    c1, c2 = st.columns([2, 1])
    
    with c1:
        fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                     title=f"Curva de Maturação - {estado_sel}",
                     template="plotly_white")
        fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.subheader("📊 Projeção Mensal")
        st.dataframe(
            df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
            height=450,
            use_container_width=True
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
    st.error(f"❌ Arquivo '{NOME_ARQUIVO}' não encontrado no GitHub.")
    st.info("Verifique se o arquivo está na raiz do repositório com o nome exato informado.")
