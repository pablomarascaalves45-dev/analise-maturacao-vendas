import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("📈 Projeção de Maturação: Analisador de Planilha")
st.markdown("---")

# 2. CAMPO PARA SUBIR O ARQUIVO
st.sidebar.header("📁 Importar Dados")
arquivo_subido = st.sidebar.file_uploader(
    "Suba sua planilha:", 
    type=["xlsx", "xls", "csv"]
)

if arquivo_subido is not None:
    try:
        # LÓGICA DE LEITURA REFORÇADA
        # Verificamos o conteúdo real do arquivo, não apenas a extensão no nome
        if "csv" in arquivo_subido.name.lower():
            # Tenta ler como CSV com separador de vírgula (padrão do seu arquivo)
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)

        # Limpeza: Remover colunas totalmente vazias que o Excel às vezes cria
        df_growth = df_growth.dropna(axis=1, how='all')

        # --- SIDEBAR DE PARÂMETROS ---
        st.sidebar.header("⚙️ Configurações")
        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Estudo 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        # Identifica colunas RS, SC, PR
        estados_alvo = ["RS", "SC", "PR"]
        
        # Pegamos apenas colunas que contêm os nomes dos estados
        colunas_disponiveis = [c for c in df_growth.columns if any(est in str(c) for est in estados_alvo)]
        
        if colunas_disponiveis:
            estado_sel = st.sidebar.selectbox("Escolha o Estado para análise:", estados_alvo)
            
            # Localiza a coluna correta (se houver duplicada, pegamos a última que costuma ter os dados)
            cols_matching = [c for c in df_growth.columns if estado_sel in str(c)]
            col_nome_real = cols_matching[-1] 
            
            # Converte valores para numérico (taxas de crescimento)
            taxas = pd.to_numeric(df_growth[col_nome_real], errors='coerce').fillna(0).values

            projecao = []
            # Mês 1: 60% do valor alvo
            valor_atual = valor_estudo * 0.6 
            projecao.append(valor_atual)
            
            # Cálculo dos 36 meses
            for i in range(1, 36):
                if i < len(taxas):
                    taxa_mes = taxas[i]
                    valor_atual = valor_atual * (1 + taxa_mes)
                    projecao.append(valor_atual)
            
            # DataFrame para o Dashboard
            df_res = pd.DataFrame({
                "Mês": range(1, len(projecao) + 1),
                "Faturamento": projecao
            })
            df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100

            # --- EXIBIÇÃO ---
            c1, c2 = st.columns([2, 1])
            
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                             title=f"Evolução de Faturamento - {estado_sel}",
                             template="plotly_white",
                             color_discrete_sequence=["#00CC96"])
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                fig.update_layout(yaxis_tickformat="R$,.2f")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("📊 Tabela de Dados")
                st.dataframe(
                    df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                    height=450, use_container_width=True
                )

            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Venda Mês 1", f"R$ {projecao[0]:,.2f}")
            m2.metric("Venda Mês 36", f"R$ {projecao[-1]:,.2f}")
            
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Acima de 36m"
            m3.metric("Maturação (100%)", f"Mês {mes_mat}")

        else:
            st.warning("⚠️ Estados não encontrados. Verifique se as colunas RS, SC ou PR existem na planilha.")
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo: Verifique se o formato está correto.")
        st.info(f"Detalhe técnico: {e}")
else:
    st.info("👋 Por favor, suba o arquivo para iniciar a análise.")
