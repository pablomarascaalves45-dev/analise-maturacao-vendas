import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

# --- BASE DE DADOS INTEGRADA (VALORES EXATOS DA SUA PLANILHA) ---
data_curva = {
    "RS": [0.0, 0.0079, 0.0163, 0.026, 0.0264, -0.0112, 0.0366, 0.0048, 0.0503, -0.0111, 0.0362, 0.0411, 0.0076, -0.0021, 0.0056, -0.0042, 0.0159, 0.0315, 0.0039, 0.0019, 0.0016, 0.0032, 0.0055, 0.0013, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "SC": [0.0, -0.0038, 0.0365, 0.0035, 0.0444, 0.0042, 0.0228, 0.0118, 0.0057, 0.0037, 0.0207, 0.0752, 0.0458, -0.0242, -0.0009, -0.0186, 0.0381, 0.0416, 0.0083, 0.0163, 0.0169, 0.0113, 0.0097, 0.0135, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    "PR": [0.0, 0.0389, 0.0589, 0.0281, 0.0373, 0.0203, 0.0292, 0.0028, 0.0246, 0.0014, 0.0389, 0.0204, -0.0114, 0.0062, 0.0491, -0.0009, 0.0427, 0.0286, 0.0246, 0.0308, 0.0199, 0.0125, 0.0099, 0.0028, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
}

st.title("Projeção de Maturação: Analisador de Dados")
st.markdown("---")

# 2. CONFIGURAÇÕES DA PROJEÇÃO
st.sidebar.header("Configurações da Projeção")

valor_estudo = st.sidebar.number_input(
    "Venda Alvo (Estudo 100%):", 
    min_value=0.0, 
    value=400000.0, 
    step=10000.0
)

estados_alvo = ["RS", "SC", "PR"]
estado_sel = st.sidebar.selectbox("Estado para análise:", estados_alvo)

# Carrega as taxas exatas
taxas = data_curva[estado_sel]

# Cálculo da Projeção
projecao = []
# Mantendo sua regra de percentual inicial
percentual_inicial = 0.77 if estado_sel == "RS" else 0.60
valor_atual = valor_estudo * percentual_inicial
projecao.append(valor_atual)

# Aplica as taxas mês a mês (1 a 35)
for i in range(1, 36):
    taxa_mes = taxas[i]
    valor_atual = valor_atual * (1 + taxa_mes)
    projecao.append(valor_atual)

df_res = pd.DataFrame({
    "Mês": range(1, len(projecao) + 1),
    "Faturamento": projecao
})
df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100
meses_grafico = [1, 3, 6, 9, 12, 18, 24, 30, 36]

# --- VISUALIZAÇÃO ---
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

# Métricas de destaque
st.markdown("---")
m1, m12, m2, m3 = st.columns(4)
m1.metric("Venda Inicial (Mês 1)", f"R$ {projecao[0]:,.2f}", delta=f"{int(percentual_inicial*100)}% do Alvo")
v_12 = projecao[11]
m12.metric("Venda 12 Meses", f"R$ {v_12:,.2f}", delta=f"{(v_12/valor_estudo)*100:.2f}% do Alvo")
v_final = projecao[-1]
m2.metric("Venda Final (Mês 36)", f"R$ {v_final:,.2f}", delta=f"{(v_final/valor_estudo)*100:.2f}% do Alvo")
atingiu = df_res[df_res["% Maturação"] >= 100]
mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Acima de 36m"
m3.metric("Maturação (100%)", f"Mês {mes_mat}")

# --- SEÇÃO DE HISTÓRICO E DRE (CÓDIGO ORIGINAL MANTIDO) ---
# [Aqui continua o seu código de upload de histórico e DRE conforme você já tinha]
