import pandas as pd
import plotly.express as px
import streamlit as st
import os

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação de Lojas", layout="wide")

st.title("📈 Analisador de Curva de Maturação")
st.markdown("---")

# 2. CONFIGURAÇÃO DO ARQUIVO (NOME NO SEU GITHUB)
# Se você renomeou no Git para crescimento.csv, use esse nome abaixo
NOME_ARQUIVO = "crescimento.csv.xlsx - Sheet1.csv" 

def carregar_dados(caminho):
    if os.path.exists(caminho):
        # decimal=',' é crucial porque sua planilha usa o padrão brasileiro
        return pd.read_csv(caminho, decimal=',', engine='python')
    return None

df_growth = carregar_dados(NOME_ARQUIVO)

if df_growth is not None:
    # --- SIDEBAR ---
    st.sidebar.header("⚙️ Parâmetros do Estudo")
    
    # Valor 100% da loja
    valor_estudo = st.sidebar.number_input(
        "Venda Alvo (Estudo 100%):", 
        min_value=0.0, 
        value=400000.0, 
        step=10000.0,
        format="%.2f"
    )
    
    # Identifica colunas RS, SC, PR (limpando possíveis duplicatas)
    cols_base = [c for c in df_growth.columns if c in ["RS", "SC", "PR"]]
    estados = list(dict.fromkeys(cols_base))
    
    estado_sel = st.sidebar.selectbox("Selecione o Estado:", estados)
    
    st.sidebar.markdown("---")
    st.sidebar.write(f"**Venda Inicial (Mês 1):** R$ {valor_estudo * 0.6:,.2f}")

    # --- CÁLCULO DA MATURAÇÃO ---
    # Pegamos a coluna do estado selecionado
    col_dados = df_growth[estado_sel]
    # Se houver duas colunas com o mesmo nome, pegamos a primeira
    if isinstance(col_dados, pd.DataFrame):
        taxas = pd.to_numeric(col_dados.iloc[:, 0], errors='coerce').fillna(0).values
    else:
        taxas = pd.to_numeric(col_dados, errors='coerce').fillna(0).values

    projecao = []
    # Regra de Negócio: Mês 1 é sempre 60% do valor de estudo
    venda_atual = valor_estudo * 0.6
    projecao.append(venda_atual)
    
    # Mês 2 ao 36: Aplica a taxa de crescimento sobre o valor do mês anterior
    for i in range(1, 36):
        if i < len(taxas):
            taxa_mes = taxas[i]
            venda_atual = venda_atual * (1 + taxa_mes)
            projecao.append(venda_atual)
    
    # Criar DataFrame Final
    df_plot = pd.DataFrame({
        "Mês": range(1, len(projecao) + 1),
        "Faturamento": projecao
    })
    df_plot["% Maturação"] = (df_plot["Faturamento"] / valor_estudo) * 100

    # --- DASHBOARD ---
    c1, c2 = st.columns([2, 1])
    
    with c1:
        st.subheader(f"Projeção de Vendas: {estado_sel}")
        fig = px.line(
            df_plot, x="Mês", y="Faturamento", 
            markers=True,
            labels={"Faturamento": "Venda Projetada (R$)"},
            template="plotly_dark"
        )
        # Linha de Meta (100% do estudo)
        fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta (100%)")
        st.plotly_chart(fig, use_container_width=True)
        
    with c2:
        st.subheader("📊 Tabela Mensal")
        st.dataframe(
            df_plot.style.format({
                "Faturamento": "R$ {:,.2f}",
                "% Maturação": "{:.2f}%"
            }),
            height=450,
            use_container_width=True
        )

    # --- MÉTRICAS ---
    st.markdown("---")
    m1, m2, m3 = st.columns(3)
    m1.metric("Venda Mês 1", f"R$ {projecao[0]:,.2f}")
    m2.metric("Venda Mês 36", f"R$ {projecao[-1]:,.2f}")
    
    atingiu = df_plot[df_plot["% Maturação"] >= 100]
    mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Acima de 36 meses"
    m3.metric("Mês de Maturação", f"Mês {mes_mat}")

else:
    st.error(f"Arquivo '{NOME_ARQUIVO}' não encontrado no repositório.")
    st.info("💡 Dica: Verifique se o nome do arquivo no GitHub é exatamente o mesmo que está na linha 14 do código.")
