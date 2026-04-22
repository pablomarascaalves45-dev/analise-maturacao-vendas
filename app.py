import pandas as pd
import plotly.express as px
import streamlit as st
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Curva de Maturação", layout="wide")

# CSS PARA CONGELAR COLUNAS (0 A 4) E CABEÇALHO (LINHAS 1 E 2)
st.markdown("""
    <style>
    .sticky-container {
        overflow: auto;
        max-height: 650px;
        border: 1px solid #e6e9ef;
        position: relative;
    }
    table {
        border-collapse: separate;
        border-spacing: 0;
        width: 100%;
        font-family: sans-serif;
    }
    /* Fixar Cabeçalho Superior */
    thead th {
        position: sticky;
        top: 0;
        z-index: 10;
        background-color: #ffffff !important;
        border-bottom: 2px solid #ccc !important;
        padding: 10px;
    }
    /* Fixar Colunas da Esquerda (Índices e Nomes de Conta - 0 a 4) */
    th:nth-child(-n+5), 
    td:nth-child(-n+5) {
        position: sticky;
        left: 0;
        z-index: 8;
        background-color: #ffffff !important;
        border-right: 1px solid #ddd !important;
        min-width: 150px;
    }
    /* Célula de cruzamento (topo esquerdo) precisa de z-index superior */
    thead th:nth-child(-n+5) {
        z-index: 11;
    }
    /* Estilo para as linhas de destaque */
    .highlight-row {
        background-color: #f0f7ff !important;
        font-weight: bold !important;
    }
    td {
        padding: 8px;
        border-bottom: 1px solid #eee;
        white-space: nowrap;
    }
    </style>
""", unsafe_allow_html=True)

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
        valor_estudo = st.sidebar.number_input("Venda Alvo (Estudo 100%):", min_value=0.0, value=400000.0, step=10000.0)
        
        estados_alvo = ["RS", "SC", "PR"]
        colunas_disponiveis = [c for c in df_growth.columns if any(est in str(c) for est in estados_alvo)]
        
        if colunas_disponiveis:
            estado_sel = st.sidebar.selectbox("Estado para análise:", estados_alvo)
            cols_matching = [c for c in df_growth.columns if estado_sel in str(c)]
            col_nome_real = cols_matching[-1] 
            taxas = pd.to_numeric(df_growth[col_nome_real], errors='coerce').fillna(0).values

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
                fig = px.line(df_res, x="Mês", y="Faturamento", title=f"Evolução Projetada - {estado_sel}", template="plotly_white", markers=True)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.subheader("Marcos de Maturação")
                st.dataframe(df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}), height=400)

    except Exception as e:
        st.error(f"Erro na Projeção: {e}")

# --- SEÇÃO DRE ---
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")

arquivo_dre = st.sidebar.file_uploader("Upload da planilha de DRE:", type=["xlsx", "xls", "csv"], key="dre_file")

if arquivo_dre is not None:
    try:
        df_dre_raw = pd.read_excel(arquivo_dre, header=None)
        
        # Lógica de extração de valores (Inalterada)
        termos = {"RB": "Receita Bruta", "MC": "Margem de Contribuição", "PVL": "Perdas Vencidos Liquido", "RES": "Resultado Operacional"}
        indices = {}
        for chave, texto in termos.items():
            match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains(texto, case=False, na=False)]
            if not match.empty: indices[chave] = match.index[0]

        # Indicadores no topo
        c1, c2, c3 = st.columns(3)
        if "RB" in indices: c1.metric("Faturamento", f"R$ {df_dre_raw.iloc[indices['RB'], 3]:,.2f}")
        if "MC" in indices: c2.metric("Margem", f"R$ {df_dre_raw.iloc[indices['MC'], 3]:,.2f}")
        if "RES" in indices: c3.metric("Resultado", f"R$ {df_dre_raw.iloc[indices['RES'], 3]:,.2f}")

        st.markdown("---")
        st.subheader("Tabela de Dados Financeiros Detalhada")
        
        df_exibicao = df_dre_raw.dropna(axis=1, how='all').fillna("")

        # Identificação de colunas para formatação
        colunas_avri = []
        colunas_realizado = []
        for col_idx in range(len(df_exibicao.columns)):
            cabecalho_texto = df_exibicao.iloc[0:4, col_idx].astype(str).str.upper()
            if cabecalho_texto.str.contains("AV-RI|AV-RL").any(): colunas_avri.append(df_exibicao.columns[col_idx])
            if cabecalho_texto.str.contains("REALIZADO").any(): colunas_realizado.append(df_exibicao.columns[col_idx])

        # Formatadores
        def formatador_porcentagem(val):
            try: return f"{float(str(val).replace(',', '.')) * 100:.2f}%".replace('.', ',')
            except: return val

        def formatador_inteiro(val):
            try: return f"{int(round(float(str(val).replace(',', '.')))):,}".replace(',', '.')
            except: return val

        contas_destaque = ["Receita Bruta", "Deduções", "Receita Líquida", "CMV", "Perdas Vencidos Liquido", "Discrepância _ Estoque", "Margem de Contribuição", "Despesas Folha", "Despesas ADM", "Despesas Operação", "Resultado Operacional"]

        def aplicar_classe_destaque(row):
            texto = str(row.iloc[1]).strip()
            if any(conta.lower() in texto.lower() for conta in contas_destaque):
                return ['highlight-row'] * len(row)
            return [''] * len(row)

        col_pct_alvo = list(set([2] + colunas_avri))
        
        # Gerar HTML da Tabela com Estilo Aplicado
        df_html = (
            df_exibicao.style
            .apply(aplicar_classe_destaque, axis=1)
            .format(subset=col_pct_alvo, formatter=formatador_porcentagem)
            .format(subset=colunas_realizado, formatter=formatador_inteiro)
            .hide(axis='index')
            .to_html()
        )

        # Renderizar com Container de Scroll e Sticky
        st.markdown(f'<div class="sticky-container">{df_html}</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Erro no processamento do DRE: {e}")
