import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

st.title("Projeção de Maturação: Analisador de Dados")
st.markdown("---")

# 2. ENTRADA DE DADOS DE PROJEÇÃO
st.sidebar.header("Dados de Projeção")
arquivo_subido = st.sidebar.file_uploader(
    "Upload da planilha de Taxas de Crescimento:", 
    type=["xlsx", "xls", "csv"],
    key="proj_file"
)

taxas = [] 

if arquivo_subido is not None:
    try:
        if "csv" in arquivo_subido.name.lower():
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)

        df_growth = df_growth.dropna(axis=1, how='all')

        st.sidebar.header("Configurações da Projeção")
        valor_estudo = st.sidebar.number_input(
            "Venda Alvo (Estudo 100%):", 
            min_value=0.0, 
            value=400000.0, 
            step=10000.0
        )
        
        estados_alvo = ["RS", "SC", "PR"]
        colunas_disponiveis = [c for c in df_growth.columns if any(est in str(c) for est in estados_alvo)]
        
        if colunas_disponiveis:
            estado_sel = st.sidebar.selectbox("Estado para análise:", estados_alvo)
            cols_matching = [c for c in df_growth.columns if estado_sel in str(c)]
            col_nome_real = cols_matching[-1] 
            
            # Tratamento de taxas
            raw_taxas = pd.to_numeric(df_growth[col_nome_real], errors='coerce').fillna(0).values
            taxas = [t/100 if abs(t) > 1 else t for t in raw_taxas]

            projecao = []
            percentual_inicial = 0.77 if estado_sel == "RS" else 0.60
            valor_atual = valor_estudo * percentual_inicial
            projecao.append(valor_atual)
            
            for i in range(1, 36):
                if i < len(taxas):
                    valor_atual = valor_atual * (1 + taxas[i])
                    projecao.append(valor_atual)
            
            df_res = pd.DataFrame({"Mês": range(1, len(projecao) + 1), "Faturamento": projecao})
            df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100
            
            c1, c2 = st.columns([2, 1])
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, title=f"Evolução Projetada - {estado_sel}")
                fig.update_layout(yaxis_tickformat="R$,.2f")
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.subheader("Marcos de Maturação")
                st.dataframe(df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}), height=400)

    except Exception as e:
        st.error(f"Erro na Projeção: {e}")

# --- SEÇÃO DRE: ANÁLISE FINANCEIRA ---
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")

arquivo_dre = st.sidebar.file_uploader("Upload da planilha de DRE:", type=["xlsx", "xls", "csv"], key="dre_file")

if arquivo_dre is not None:
    try:
        # Lê a planilha original (sem pular colunas para manter os índices originais)
        df_dre_raw = pd.read_excel(arquivo_dre, header=None)
        
        # Mapeamento de linhas (fórmulas originais mantidas)
        termos = {
            "RB": "Receita Bruta", "MC": "Margem de Contribuição",
            "PVL": "Perdas Vencidos Liquido", "DISC": "Discrepância _ Estoque",
            "FOLHA": "Despesas Folha", "ADM": "Despesas ADM",
            "OPER": "Despesas Operação", "RES": "Resultado Operacional"
        }

        indices = {}
        for chave, texto in termos.items():
            match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains(texto, case=False, na=False)]
            if not match.empty:
                indices[chave] = match.index[0]

        def pegar_v(chave):
            if chave in indices:
                val = df_dre_raw.iloc[indices[chave], 3] 
                return pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0.0
            return 0.0

        vals = {k: pegar_v(k) for k in termos.keys()}

        # Cards de Indicadores
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento", f"R$ {vals['RB']:,.2f}")
        c2.metric("Margem de Contribuição", f"R$ {vals['MC']:,.2f}")
        c3.metric("Resultado Operacional", f"R$ {vals['RES']:,.2f}", delta_color="normal" if vals['RES'] >= 0 else "inverse")
        perdas_totais = abs(vals['PVL']) + abs(vals['DISC'])
        c4.metric("Perdas e Discrepâncias", f"R$ {perdas_totais:,.2f}")

        # Gráfico de Ofensores
        st.markdown("### Composição de Gastos")
        df_gastos = pd.DataFrame({
            "Conta": ["Folha", "ADM", "Operação", "Quebra/Perdas"],
            "Valor": [abs(vals['FOLHA']), abs(vals['ADM']), abs(vals['OPER']), perdas_totais]
        })
        fig_of = px.pie(df_gastos, values='Valor', names='Conta', hole=0.4)
        st.plotly_chart(fig_of, use_container_width=True)

        # --- TABELA DETALHADA COM AJUSTE DE PORCENTAGEM (COLUNA 3 / ÍNDICE 2) ---
        st.markdown("---")
        st.subheader("Tabela de Dados Financeiros Detalhada")
        
        # Criamos uma cópia para exibição
        df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")

        # Função de formatação para a coluna %Meta (Índice 2)
        # Ela pula as primeiras 2 linhas e formata números como porcentagem (x100)
        def formatador_porcentagem(val):
            try:
                # Tenta converter para número
                num = pd.to_numeric(val)
                if pd.isna(num) or isinstance(val, str): 
                    return val
                # Se for número, multiplica por 100 e coloca %
                return f"{num * 100:.2f}%"
            except:
                # Se for texto (título da coluna ou hifen), retorna como está
                return val

        # Aplicando a formatação segura apenas na coluna de índice 2
        # As outras colunas permanecem com a formatação padrão do Streamlit
        st.dataframe(
            df_exibicao.style.format(subset=[2], formatter=formatador_porcentagem),
            use_container_width=True, 
            hide_index=True
        )

    except Exception as e:
        st.error(f"Erro no processamento do DRE: {e}")
