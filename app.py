import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

# --- BASE DE DADOS INTEGRADA (Taxas de Crescimento) ---
# Dados extraídos do arquivo "Curva de crescimento.xlsx"
data_growth = {
    "Mes": list(range(1, 37)),
    "RS": [0.0, 0.08, 0.07, 0.04, 0.03, 0.02, 0.02, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    "SC": [0.0, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00],
    "PR": [0.0, 0.12, 0.10, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00]
}
df_growth_fixed = pd.DataFrame(data_growth)

st.title("Projeção de Maturação: Analisador de Dados")
st.markdown("---")

# 2. CONFIGURAÇÕES DA PROJEÇÃO (Sidebar)
st.sidebar.header("Configurações da Projeção")

valor_estudo = st.sidebar.number_input(
    "Venda Alvo (Estudo 100%):", 
    min_value=0.0, 
    value=400000.0, 
    step=10000.0
)

estados_alvo = ["RS", "SC", "PR"]
estado_sel = st.sidebar.selectbox("Estado para análise:", estados_alvo)

# Lógica de Projeção usando a base fixa
taxas = df_growth_fixed[estado_sel].values
projecao = []
percentual_inicial = 0.77 if estado_sel == "RS" else 0.60
valor_atual = valor_estudo * percentual_inicial
projecao.append(valor_atual)

for i in range(1, 36):
    taxa_mes = taxas[i]
    valor_atual = valor_atual * (1 + taxa_mes)
    projecao.append(valor_atual)

df_res = pd.DataFrame({
    "Mês": range(1, len(projecao) + 1),
    "Faturamento": projecao
})
df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100

# --- VISUALIZAÇÃO DA PROJEÇÃO ---
c1, c2 = st.columns([2, 1])
meses_grafico = [1, 3, 6, 9, 12, 18, 24, 30, 36]

with c1:
    fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                 title=f"Evolução de Faturamento Projetada - {estado_sel}",
                 template="plotly_white", color_discrete_sequence=["#00CC96"])
    fig.update_layout(xaxis=dict(tickmode='array', tickvals=meses_grafico), yaxis_tickformat="R$,.2f")
    fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
    fig.add_vline(x=12, line_dash="dot", line_color="orange", annotation_text="Corte 12 Meses")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Marcos de Maturação")
    st.dataframe(df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                height=450, use_container_width=True, hide_index=True)

# Métricas
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

# --- SEÇÃO: HISTÓRICO REAL (Mantido como Upload) ---
st.markdown("### Histórico Real vs Crescimento Projetado")
arquivo_historico = st.sidebar.file_uploader("Upload Vendas Realizadas (Histórico):", type=["xlsx", "csv"], key="hist_file")

if arquivo_historico:
    try:
        df_hist = pd.read_excel(arquivo_historico) if "xls" in arquivo_historico.name else pd.read_csv(arquivo_historico)
        if 'Desc_Filial' in df_hist.columns:
            filiais = sorted(df_hist['Desc_Filial'].unique())
            filial_sel = st.selectbox("Unidade para análise:", filiais)
            df_loja = df_hist[df_hist['Desc_Filial'] == filial_sel].sort_values(by='AnoMes').copy()
            
            # Cálculo do esperado baseado no primeiro mês real
            v_ini_real = df_loja['Mercadoria'].iloc[0]
            esperado = [v_ini_real]
            for i in range(1, len(df_loja)):
                esperado.append(esperado[-1] * (1 + taxas[i] if i < len(taxas) else 1))
            
            df_loja['Crescimento_Esperado'] = esperado
            fig_hist = px.bar(df_loja, x='AnoMes', y='Mercadoria', title=f"Real vs Projeção: {filial_sel}")
            fig_hist.add_scatter(x=df_loja['AnoMes'], y=df_loja['Crescimento_Esperado'], name='Projeção Estado', line=dict(color='orange'))
            st.plotly_chart(fig_hist, use_container_width=True)
    except Exception as e:
        st.error(f"Erro no Histórico: {e}")

# --- SEÇÃO DRE (Mantido como Upload) ---
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")
arquivo_dre = st.sidebar.file_uploader("Upload da planilha de DRE:", type=["xlsx", "xls", "csv"], key="dre_file")
# ... (Mantive a lógica original do DRE que você já possui)
