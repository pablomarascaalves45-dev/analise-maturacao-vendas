import streamlit as st
import pandas as pd
import plotly.express as px

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Análise de Lojas Negativas", layout="wide")

st.title("Análise Estratégica: Performance de Unidades Negativas")
st.markdown("---")

# 2. FUNÇÃO DE LIMPEZA E CARREGAMENTO
@st.cache_data
def load_data(file):
    df = pd.read_excel(file)
    
    # Lista de colunas financeiras para garantir que sejam float
    cols_financeiras = ['RO Mês', 'RO Acum', 'Aluguel Mês', '%RO Mês', '%RO Acum', '%Aluguel Mês']
    
    for col in cols_financeiras:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = (df[col].astype(str)
                           .str.replace('R$', '', regex=False)
                           .str.replace('%', '', regex=False)
                           .str.replace('.', '', regex=False)
                           .str.replace(',', '.', regex=False)
                           .strip())
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
    return df

# 3. SIDEBAR - UPLOAD
st.sidebar.header("Configurações")
uploaded_file = st.sidebar.file_uploader("Carregue a planilha Excel (xlsx)", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = load_data(uploaded_file)
        
        # --- DASHBOARD DE MÉTRICAS ---
        total_prejuizo_mes = df['RO Mês'].sum()
        total_prejuizo_acum = df['RO Acum'].sum()
        
        media_aluguel_perc = df['%Aluguel Mês'].mean()
        # Ajuste de escala caso o Excel venha em decimal (ex: 0.07 vira 7.00%)
        if media_aluguel_perc < 1: media_aluguel_perc *= 100

        c1, c2, c3 = st.columns(3)
        c1.metric("Prejuízo Total (Mês)", f"R$ {total_prejuizo_mes:,.2f}")
        c2.metric("Prejuízo Acumulado", f"R$ {total_prejuizo_acum:,.2f}")
        c3.metric("Média % Aluguel", f"{media_aluguel_perc:.2f}%")

        # --- ANÁLISE GRÁFICA ---
        col_graf1, col_graf2 = st.columns(2)
        
        with col_graf1:
            st.subheader("Top 10 Unidades Críticas (Mês)")
            # As 10 lojas com os menores valores de RO (mais negativas)
            top_negativas = df.nsmallest(10, 'RO Mês')
            fig_neg = px.bar(top_negativas, x='RO Mês', y='Desc_CC', orientation='h',
                             color='RO Mês', color_continuous_scale='Reds_r')
            fig_neg.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_neg, use_container_width=True)

        with col_graf2:
            st.subheader("Aluguel vs Resultado")
            fig_scat = px.scatter(df, x='%Aluguel Mês', y='RO Mês', 
                                  hover_name='Desc_CC', size='Aluguel Mês',
                                  color='Diretor', title="Impacto do Aluguel no RO")
            st.plotly_chart(fig_scat, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Por favor, faça o upload do arquivo Excel para começar.")
