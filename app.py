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
    
    # Remove espaços em branco dos nomes das colunas
    df.columns = df.columns.str.strip()
    
    # Lista de colunas financeiras para conversão numérica
    cols_financeiras = ['RO Mês', 'RO Acum', 'Aluguel Mês', '%RO Mês', '%RO Acum', '%Aluguel Mês', 'Multa rescisória atual']
    
    for col in cols_financeiras:
        if col in df.columns:
            if df[col].dtype == 'object':
                df[col] = (df[col].astype(str)
                           .str.replace('R$', '', regex=False)
                           .str.replace('%', '', regex=False)
                           .str.replace('.', '', regex=False)
                           .str.replace(',', '.', regex=False)
                           .str.strip())
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Ajuste de escala percentual
            if col.startswith('%'):
                if df[col].abs().mean() < 1.0:
                    df[col] = df[col] * 100
            
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
        qtd_lojas = len(df) 
        media_aluguel_perc = df['%Aluguel Mês'].mean()

        c0, c1, c2, c3 = st.columns(4)
        c0.metric("Lojas Analisadas", f"{qtd_lojas}")
        c1.metric("Prejuízo Total Mês", f"R$ {total_prejuizo_mes:,.2f}")
        c2.metric("Prejuízo Acumulado", f"R$ {total_prejuizo_acum:,.2f}")
        c3.metric("Média % Aluguel", f"{media_aluguel_perc:.2f}%")

        # --- ANÁLISE GRÁFICA (MÊS) ---
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Top 10 Unidades Críticas (Mês)")
            top_negativas = df.nsmallest(10, 'RO Mês')
            fig_neg = px.bar(top_negativas, x='RO Mês', y='Desc_CC', orientation='h',
                             color='RO Mês', color_continuous_scale='Reds_r')
            fig_neg.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_neg, use_container_width=True)

        with col_graf2:
            st.subheader("Aluguel vs Resultado (Mês)")
            fig_scat = px.scatter(df, x='%Aluguel Mês', y='RO Mês', hover_name='Desc_CC', 
                                  size='Aluguel Mês', color='Diretor' if 'Diretor' in df.columns else None)
            fig_scat.update_layout(xaxis_ticksuffix="%")
            st.plotly_chart(fig_scat, use_container_width=True)

        st.markdown("---")
        
        # --- ANÁLISE GRÁFICA (ACUMULADO) ---
        col_graf3, col_graf4 = st.columns(2)
        with col_graf3:
            st.subheader("Top 10 Unidades Críticas (Acumulado)")
            top_negativas_acum = df.nsmallest(10, 'RO Acum')
            fig_neg_acum = px.bar(top_negativas_acum, x='RO Acum', y='Desc_CC', orientation='h',
                                  color='RO Acum', color_continuous_scale='Reds_r')
            fig_neg_acum.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_neg_acum, use_container_width=True)

        with col_graf4:
            st.subheader("Aluguel vs Resultado (Acumulado)")
            fig_scat_acum = px.scatter(df, x='%Aluguel Mês', y='RO Acum', hover_name='Desc_CC', 
                                       size='Aluguel Mês', color='Diretor' if 'Diretor' in df.columns else None)
            fig_scat_acum.update_layout(xaxis_ticksuffix="%")
            st.plotly_chart(fig_scat_acum, use_container_width=True)

        # --- RANKINGS DE CUSTO ---
        st.markdown("---")
        col_rank1, col_rank2 = st.columns(2)
        with col_rank1:
            st.subheader("Top 10 Maiores Aluguéis")
            top_aluguel = df.nlargest(10, 'Aluguel Mês')
            fig_aluguel = px.bar(top_aluguel, x='Aluguel Mês', y='Desc_CC', orientation='h',
                                 color='Aluguel Mês', color_continuous_scale='Blues')
            st.plotly_chart(fig_aluguel, use_container_width=True)

        with col_rank2:
            st.subheader("Top 10 Maiores Multas")
            if 'Multa rescisória atual' in df.columns:
                top_multa = df.nlargest(10, 'Multa rescisória atual')
                fig_multa = px.bar(top_multa, x='Multa rescisória atual', y='Desc_CC', orientation='h',
                                   color='Multa rescisória atual', color_continuous_scale='Oranges')
                st.plotly_chart(fig_multa, use_container_width=True)

        # --- ANÁLISE DE CARACTERÍSTICAS DOS PONTOS ---
        st.markdown("---")
        st.subheader("Análise Qualitativa: Características dos Pontos Críticos")
        cols_perfil = ["Posição Loja", "Próximo a mercado", "Vagas", "Calçadão", "Loja atualizada"]
        cols_existentes = [c for c in cols_perfil if c in df.columns]

        if cols_existentes:
            c_p1, c_p2 = st.columns(2)
            for idx, col in enumerate(cols_existentes):
                target = c_p1 if idx % 2 == 0 else c_p2
                df_p = df[col].value_counts().reset_index()
                df_p.columns = [col, 'Quantidade']
                fig = px.pie(df_p, values='Quantidade', names=col, title=f"Perfil: {col}", hole=0.4)
                target.plotly_chart(fig, use_container_width=True)

        # --- NOVA SEÇÃO: ANÁLISE DE CONCORRÊNCIA ---
        st.markdown("---")
        st.subheader("Análise de Concorrência: Impacto na Performance")
        
        concorrentes_lista = ["SaoJoao", "Independente", "Panvel", "Raia", "Morifarma", "Nissei", "PPCatarinense", "Pacheco", "FarmTrabalhador"]
        cols_conc_encontradas = [c for c in df.columns if any(conc.lower() in c.lower() for conc in concorrentes_lista)]

        if cols_conc_encontradas:
            # Consolida dados de presença (considera qualquer marcação 'Sim', 'X', 'S' ou número > 0)
            contagem_concorrentes = {}
            for col in cols_conc_encontradas:
                filtro_presenca = df[col].astype(str).str.lower().isin(['sim', 'x', 's', '1', '1.0'])
                contagem_concorrentes[col] = df[filtro_presenca].shape[0]
            
            df_conc = pd.DataFrame(list(contagem_concorrentes.items()), columns=['Rede', 'Lojas Próximas'])
            df_conc = df_conc.sort_values(by='Lojas Próximas', ascending=False)

            col_c1, col_c2 = st.columns([2, 1])
            with col_c1:
                fig_conc = px.bar(df_conc, x='Rede', y='Lojas Próximas', 
                                  title="Incidência de Concorrentes nas Unidades Negativas",
                                  color='Lojas Próximas', color_continuous_scale='Turbo')
                st.plotly_chart(fig_conc, use_container_width=True)
            with col_c2:
                st.info("**Análise de Densidade**")
                st.write("O gráfico ao lado indica quais bandeiras concorrentes possuem maior sobreposição geográfica com suas unidades de baixo desempenho. Uma alta frequência de 'SaoJoao' ou 'Panvel' pode indicar saturação de mercado nessas praças específicas.")
        else:
            st.info("Colunas de concorrentes não identificadas na planilha.")

        # --- COMPARAÇÃO DE REPETIÇÃO ---
        st.markdown("---")
        st.subheader("Cruzamento de Dados: Unidades Críticas Recorrentes")
        
        lojas_mes = set(top_negativas['Desc_CC'])
        lojas_acum = set(top_negativas_acum['Desc_CC'])
        lojas_repetidas = sorted(list(lojas_mes.intersection(lojas_acum)))
        
        if lojas_repetidas:
            st.write(f"Lojas presentes no Top 10 (Mês e Acumulado): {len(lojas_repetidas)}")
            cols = st.columns(len(lojas_repetidas)) 
            for i, loja in enumerate(lojas_repetidas):
                dados_loja = df[df['Desc_CC'] == loja].iloc[0]
                with cols[i]:
                    st.info(f"**{loja}**\n\nRO Mês: R$ {dados_loja['RO Mês']:,.2f}\n\nRO Acum: R$ {dados_loja['RO Acum']:,.2f}\n\nAluguel: R$ {dados_loja['Aluguel Mês']:,.2f}")
        else:
            st.write("Não há recorrência de lojas entre os rankings.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
else:
    st.info("Aguardando upload da planilha de Lojas Negativas.")
