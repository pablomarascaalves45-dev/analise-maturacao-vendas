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
        # Leitura flexível para CSV ou Excel
        if "csv" in arquivo_subido.name.lower():
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)

        # Limpeza de colunas vazias
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
            
            # Localiza a coluna de taxas (última ocorrência do nome do estado)
            cols_matching = [c for c in df_growth.columns if estado_sel in str(c)]
            col_nome_real = cols_matching[-1] 
            
            taxas = pd.to_numeric(df_growth[col_nome_real], errors='coerce').fillna(0).values

            # --- CÁLCULO DA PROJEÇÃO ---
            projecao = []
            
            # Regra de faturamento inicial: RS = 77%, outros = 60%
            percentual_inicial = 0.77 if estado_sel == "RS" else 0.60
            valor_atual = valor_estudo * percentual_inicial
            projecao.append(valor_atual)
            
            # Cálculo dos 36 meses subsequentes
            for i in range(1, 36):
                if i < len(taxas):
                    taxa_mes = taxas[i]
                    valor_atual = valor_atual * (1 + taxa_mes)
                    projecao.append(valor_atual)
            
            # Criar DataFrame principal
            df_res = pd.DataFrame({
                "Mês": range(1, len(projecao) + 1),
                "Faturamento": projecao
            })
            df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100

            # Marcos para o eixo X do Gráfico
            meses_grafico = [1, 3, 6, 9, 12, 18, 24, 30, 36]

            # --- EXIBIÇÃO DASHBOARD ---
            c1, c2 = st.columns([2, 1])
            
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                             title=f"Evolução de Faturamento - {estado_sel} (Início {int(percentual_inicial*100)}%)",
                             template="plotly_white",
                             color_discrete_sequence=["#00CC96"])
                
                # Ajusta apenas as marcações do eixo X no gráfico
                fig.update_layout(
                    xaxis=dict(tickmode='array', tickvals=meses_grafico),
                    yaxis_tickformat="R$,.2f"
                )
                
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", annotation_text="Meta 100%")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("📊 Marcos de Maturação")
                # Exibe a tabela completa (todos os meses)
                st.dataframe(
                    df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}),
                    height=450, use_container_width=True, hide_index=True
                )

            # --- MÉTRICAS FINAIS (4 COLUNAS) ---
            st.markdown("---")
            m1, m12, m2, m3 = st.columns(4)
            
            # Venda Inicial
            m1.metric("Venda Inicial (Mês 1)", f"R$ {projecao[0]:,.2f}", 
                      delta=f"{int(percentual_inicial*100)}% do Alvo", delta_color="normal")
            
            # Venda 12 Meses
            v_12 = projecao[11] if len(projecao) >= 12 else 0
            m12.metric("Venda 12 Meses", f"R$ {v_12:,.2f}")
            
            # Venda Final
            m2.metric("Venda Final (Mês 36)", f"R$ {projecao[-1]:,.2f}")
            
            # Mês de Maturação
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Acima de 36m"
            m3.metric("Maturação (100%)", f"Mês {mes_mat}")

        else:
            st.warning("⚠️ Estados RS, SC ou PR não detectados no arquivo.")
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo.")
        st.info(f"Detalhe: {e}")
else:
    st.info("👋 Por favor, suba sua planilha para iniciar a análise.")
