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
        if "csv" in arquivo_subido.name.lower():
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)

        df_growth = df_growth.dropna(axis=1, how='all')

        # --- SIDEBAR DE PARÂMETROS ---
        st.sidebar.header("⚙️ Configurações")
        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Estudo 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        estados_alvo = ["RS", "SC", "PR"]
        colunas_disponiveis = [c for c in df_growth.columns if any(est in str(c) for est in estados_alvo)]
        
        if colunas_disponiveis:
            estado_sel = st.sidebar.selectbox("Escolha o Estado para análise:", estados_alvo)
            
            cols_matching = [c for c in df_growth.columns if estado_sel in str(c)]
            col_nome_real = cols_matching[-1] 
            
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
            
            # DataFrame Completo
            df_res = pd.DataFrame({
                "Mês": range(1, len(projecao) + 1),
                "Faturamento": projecao
            })
            df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100

            # --- FILTRAR MESES ESPECÍFICOS ---
            # Meses solicitados: 1 (como o 0/inicial), 3, 6, 9, 12, 18, 24, 30, 36
            meses_filtro = [1, 3, 6, 9, 12, 18, 24, 30, 36]
            df_filtrado = df_res[df_res["Mês"].isin(meses_filtro)].copy()

            # --- EXIBIÇÃO ---
            c1, c2 = st.columns([2, 1])
            
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                             title=f"Evolução de Faturamento - {estado_sel}",
                             template="plotly_white",
                             color_discrete_sequence=["#00CC96"])
                
                # Destacar os meses específicos no eixo X
                fig.update_layout(
                    xaxis=dict(
                        tickmode='array',
                        tickvals=meses_filtro
                    ),
                    yaxis_tickformat="R$,.2f"
                )
                
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("📊 Marcos de Maturação")
                # Exibe apenas os meses do filtro na tabela
                st.dataframe(
                    df_filtrado.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                    height=450, use_container_width=True, hide_index=True
                )

            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Venda Inicial (Mês 1)", f"R$ {projecao[0]:,.2f}")
            m2.metric("Venda Final (Mês 36)", f"R$ {projecao[-1]:,.2f}")
            
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Acima de 36m"
            m3.metric("Maturação (100%)", f"Mês {mes_mat}")

        else:
            st.warning("⚠️ Estados não encontrados.")
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo.")
        st.info(f"Detalhe: {e}")
else:
    st.info("👋 Por favor, suba o arquivo para iniciar a análise.")
