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
    "Suba sua planilha (Excel ou CSV):", 
    type=["xlsx", "xls", "csv"]
)

if arquivo_subido is not None:
    try:
        # Identifica o tipo de arquivo e lê
        if arquivo_subido.name.endswith('.csv'):
            # O seu arquivo usa vírgula como decimal e possui colunas extras
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)

        # --- SIDEBAR DE PARÂMETROS ---
        st.sidebar.header("⚙️ Configurações")
        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Estudo 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        # Limpeza de colunas: No seu arquivo, as taxas reais estão nas colunas que o pandas
        # renomeia com '.1' ou as últimas ocorrências de RS, SC, PR.
        # Vamos buscar todas que contenham os estados alvo.
        estados_alvo = ["RS", "SC", "PR"]
        colunas_encontradas = [c for c in df_growth.columns if any(est in c for est in estados_alvo)]
        
        if colunas_encontradas:
            # Criamos um seletor amigável para o usuário
            estado_sel = st.sidebar.selectbox("Escolha o Estado para análise:", estados_alvo)
            
            # --- LÓGICA PARA PEGAR A COLUNA CORRETA ---
            # No seu arquivo especificamente, as taxas estão na segunda aparição do nome do estado
            # Tentamos pegar a coluna exata ou a que termina com .1
            col_nome_real = estado_sel
            if f"{estado_sel}.1" in df_growth.columns:
                col_nome_real = f"{estado_sel}.1"
            
            # Converte para numérico e remove valores nulos
            taxas = pd.to_numeric(df_growth[col_nome_real], errors='coerce').fillna(0).values

            projecao = []
            # Regra: Mês 1 = 60% do valor alvo
            valor_atual = valor_estudo * 0.6 
            projecao.append(valor_atual)
            
            # Cálculo dos meses seguintes (até o mês 36 ou limite da planilha)
            # Começamos do índice 1 da planilha (Mês 2)
            for i in range(1, 36):
                if i < len(taxas):
                    taxa_mes = taxas[i]
                    valor_atual = valor_atual * (1 + taxa_mes)
                    projecao.append(valor_atual)
            
            # Criar DataFrame para o Gráfico
            df_res = pd.DataFrame({
                "Mês": range(1, len(projecao) + 1),
                "Faturamento": projecao
            })
            df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100

            # --- DASHBOARD ---
            c1, c2 = st.columns([2, 1])
            
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, 
                             title=f"Evolução de Faturamento - {estado_sel}",
                             template="plotly_white",
                             color_discrete_sequence=["#00CC96"])
                
                fig.add_hline(y=valor_estudo, line_dash="dash", line_color="red", 
                              annotation_text="Meta 100% (Estudo)")
                
                fig.update_layout(yaxis_tickformat="R$,.2f")
                st.plotly_chart(fig, use_container_width=True)
                
            with c2:
                st.subheader("📊 Tabela de Dados")
                st.dataframe(
                    df_res.style.format({
                        "Faturamento": "R$ {:,.2f}", 
                        "% Maturação": "{:.2f}%"
                    }),
                    height=450, use_container_width=True, hide_index=True
                )

            # MÉTRICAS TOTAIS
            st.markdown("---")
            m1, m2, m3 = st.columns(3)
            m1.metric("Venda Inicial (Mês 1)", f"R$ {projecao[0]:,.2f}")
            m2.metric("Venda Final (Mês 36)", f"R$ {projecao[-1]:,.2f}")
            
            # Cálculo de quando atinge 100%
            atingiu = df_res[df_res["% Maturação"] >= 100]
            mes_mat = atingiu["Mês"].iloc[0] if not atingiu.empty else "Não atinge em 36m"
            m3.metric("Mês de Maturação (100%)", f"Mês {mes_mat}")

        else:
            st.warning("⚠️ Não encontrei as colunas RS, SC ou PR no arquivo. Verifique o cabeçalho.")
            
    except Exception as e:
        st.error(f"Erro ao processar a planilha: {e}")
        st.info("Dica: Verifique se o arquivo não possui linhas de cabeçalho extras ou células mescladas.")
else:
    st.info("💡 Como usar: Clique no botão acima e suba o arquivo 'crescimento.csv.xlsx' para gerar a análise.")
