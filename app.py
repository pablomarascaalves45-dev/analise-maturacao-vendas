import pandas as pd
import plotly.express as px
import streamlit as st
import os

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("📈 Projeção de Maturação: Crescimento Mensal")
st.markdown("---")

# 2. CAMINHO DO ARQUIVO (NOME EXATO DO SEU GITHUB)
NOME_ARQUIVO = "crescimento.csv.xlsx - Sheet1.csv"

def carregar_dados(caminho):
    if os.path.exists(caminho):
        # Lendo com decimal=',' para converter percentuais brasileiros corretamente
        return pd.read_csv(caminho, decimal=',', engine='python')
    return None

df_growth = carregar_dados(NOME_ARQUIVO)

if df_growth is not None:
    # --- SIDEBAR DE PARÂMETROS ---
    st.sidebar.header("⚙️ Parâmetros da Loja")
    
    # Campo para definir o faturamento alvo (100%)
    valor_estudo = st.sidebar.number_input(
        "Venda Alvo (Estudo 100%):", 
        min_value=0.0, 
        value=400000.0, 
        step=10000.0
    )
    
    # Filtra colunas dos estados
    colunas_disponiveis = [c for c in df_growth.columns if c in ["RS", "SC", "PR"]]
    estados = list(dict.fromkeys(colunas_disponiveis)) # Remove duplicados
    
    if estados:
        estado_sel = st.sidebar.selectbox("Escolha o Estado:", estados)
        
        st.sidebar.markdown("---")
        st.sidebar.info(f"💡 **Início (Mês 1):** R$ {valor_estudo * 0.6:,.2f} (60%)")

        # --- CÁLCULO DA CURVA ---
        # Pega a coluna do estado e garante que os valores sejam numéricos
        col_dados = df_growth[estado_sel]
        if isinstance(col_dados, pd.DataFrame):
            taxas = pd.to_numeric(col_dados.iloc[:, 0], errors='coerce').fillna(0).values
        else:
            taxas = pd.to_numeric(col_dados, errors='coerce').fillna(0).values

        projecao = []
        # Regra: Mês 1 é sempre 60% do valor de estudo
        venda_atual = valor_estudo * 0.6
        projecao.append(venda_atual)
        
        # Mês 2 ao 36: Multiplica o valor anterior pela taxa (1 + taxa)
        for i in range(1, 36):
            if i < len(taxas):
                taxa_mes = taxas[i]
                venda_atual = venda_atual * (1 + taxa_mes)
                projecao.append(venda_atual)
        
        # DataFrame para visualização
        df_res = pd.DataFrame({
            "Mês": range(1, len(projecao) + 1),
            "Faturamento": projecao
        })
        df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100

        # --- DASHBOARD ---
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader(f"Curva de Maturação - {estado_sel}")
            fig = px.line(df_res, x="Mês", y="Faturamento", 
                         markers=True, 
                         template="plotly_white",
                         labels={"Faturamento": "Venda Projetada (R$)"})
            
            # Linha de Meta 100%
            fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", 
                          annotation_text="Meta 100%")
            st.plotly_chart(fig, use_container_width=True)
            
        with c2:
            st.subheader("📊 Tabela de Evolução")
            st.dataframe(
                df_res.style.format({
                    "Faturamento": "R$ {:,.2f}",
                    "% Maturação": "{:.2f}%"
                }),
                height=450,
                use_container_width=True,
                hide_index=True
            )

        # --- MÉTRICAS ---
        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("Venda Inicial (Mês 1)", f"R$ {projecao[0]:,.2f}")
        m2.metric("Venda Final (Mês 36)", f"R$ {projecao[-1]:,.2f}")
        
        atingiu = df_res[df_res["% Maturação"] >= 100]
        mes_100 = atingiu["Mês"].iloc[0] if not atingiu.empty else "N/A"
        m3.metric("Mês que atinge 100%", f"Mês {mes_100}")

    else:
        st.error("Colunas RS, SC ou PR não encontradas no arquivo CSV.")
else:
    st.error(f"❌ Arquivo '{NOME_ARQUIVO}' não encontrado.")
    st.info("Verifique se o arquivo está na raiz do seu repositório no GitHub.")
