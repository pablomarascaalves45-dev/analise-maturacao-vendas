import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página
st.set_page_config(page_title="Análise de Lojas Negativas", layout="wide")

st.title("Análise Estratégica: Performance de Unidades Negativas")
st.markdown("---")

# Função para carregar os dados
@st.cache_data
def load_data(file):
    df = pd.read_csv(file)
    # Limpeza básica: converter RO e Aluguel para numérico se necessário
    cols_to_fix = ['RO Mês', 'RO Acum', 'Aluguel Mês', '%RO Mês', '%Aluguel Mês']
    for col in cols_to_fix:
        if col in df.columns and df[col].dtype == 'object':
            df[col] = df[col].str.replace('.', '').str.replace(',', '.').astype(float)
    return df

# Upload do arquivo
uploaded_file = st.sidebar.file_uploader("Carregue a planilha CSV", type="csv")

if uploaded_file:
    df = load_data(uploaded_file)

    # --- 1. DASHBOARD DE MÉTRICAS ---
    total_prejuizo_mes = df['RO Mês'].sum()
    total_prejuizo_acum = df['RO Acum'].sum()
    media_aluguel_perc = df['%Aluguel Mês'].mean() * 100

    col1, col2, col3 = st.columns(3)
    col1.metric("Impacto Total (Mês)", f"R$ {total_prejuizo_mes:,.2f}", delta_color="inverse")
    col2.metric("Prejuízo Acumulado", f"R$ {total_prejuizo_acum:,.2f}", delta_color="inverse")
    col3.metric("Média % Aluguel/Fat", f"{media_aluguel_perc:.2f}%")

    # --- 2. ANÁLISE POR DIRETORIA ---
    st.subheader("Performance por Diretoria")
    df_dir = df.groupby('Diretor')[['RO Mês', 'RO Acum']].sum().reset_index()
    fig_dir = px.bar(df_dir, x='Diretor', y='RO Mês', title="Prejuízo Mensal por Diretor",
                     color='RO Mês', color_continuous_scale='Reds_r')
    st.plotly_chart(fig_dir, use_container_width=True)

    # --- 3. IDENTIFICAÇÃO DE CAUSAS (INSIGHTS) ---
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Análise de Custo de Ocupação")
        # Identificar lojas onde o aluguel é > 10% do faturamento (alerta crítico)
        df['Alerta_Aluguel'] = df['%Aluguel Mês'] > 0.10
        fig_aluguel = px.scatter(df, x='%Aluguel Mês', y='RO Mês', 
                                 hover_name='Desc_CC', size='Aluguel Mês',
                                 color='Alerta_Aluguel',
                                 title="Aluguel vs Resultado Operacional")
        st.plotly_chart(fig_aluguel, use_container_width=True)
        st.info("Lojas em azul possuem aluguel acima de 10%, o que pode ser a causa primária do RO negativo.")

    with col_right:
        st.subheader("Top 10 Lojas com Maior Prejuízo Acumulado")
        top_10 = df.nsmallest(10, 'RO Acum')
        fig_top = px.bar(top_10, x='RO Acum', y='Desc_CC', orientation='h',
                         color='RO Acum', color_continuous_scale='Reds_r')
        st.plotly_chart(fig_top, use_container_width=True)

    # --- 4. CORRELAÇÃO COM CONCORRÊNCIA ---
    st.subheader("Influência da Vizinhança no Resultado")
    conc_cols = ['SaoJoao', 'Independentes', 'Panvel', 'Raia', 'Nissei', 'Bancos ']
    # Filtrar apenas colunas que existem no DF
    available_conc = [c for c in conc_cols if c in df.columns]
    
    if available_conc:
        corr = df[available_conc + ['RO Mês']].corr()
        fig_corr = px.imshow(corr, text_auto=True, color_continuous_scale='RdBu_r',
                             title="Correlação: Concorrência vs RO Mês")
        st.plotly_chart(fig_corr, use_container_width=True)
        st.caption("Valores próximos a -1 indicam que a presença daquele concorrente reduz o resultado.")

    # --- 5. TABELA DE DADOS FILTRÁVEL ---
    st.subheader("Explorar Detalhes das Unidades")
    status_filter = st.multiselect("Filtrar por Status", df['Status_Loja_Calc'].unique(), default=df['Status_Loja_Calc'].unique())
    df_filtered = df[df['Status_Loja_Calc'].isin(status_filter)]
    
    st.dataframe(df_filtered.style.format({
        'RO Mês': 'R$ {:,.2f}',
        'RO Acum': 'R$ {:,.2f}',
        'Aluguel Mês': 'R$ {:,.2f}',
        '%Aluguel Mês': '{:.2%}'
    }))

else:
    st.info("Aguardando upload da planilha para iniciar a análise...")
