import pandas as pd
import plotly.express as px
import streamlit as st
import io
from fpdf import FPDF

# 1. CONFIGURAÇÃO DO DASHBOARD
st.set_page_config(page_title="Gestão de Maturação, DRE e Performance", layout="wide")

st.title("Sistema de Análise: Expansão e Performance")
st.markdown("---")

# --- FUNÇÕES DE UTILIDADE ---
def clean_numeric(val):
    if pd.isna(val) or val == "" or val == "-" or val == " ":
        return 0.0
    try:
        s = str(val).replace('R$', '').replace('%', '').strip()
        if ',' in s and '.' in s:
            s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            s = s.replace(',', '.')
        return float(s)
    except:
        return 0.0

@st.cache_data
def load_data_negativas(file):
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
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
            if col.startswith('%'):
                if df[col].abs().mean() < 1.0:
                    df[col] = df[col] * 100
    return df

# --- FUNÇÃO PARA GERAR PDF (SEÇÃO 3) ---
def gerar_pdf_negativas(df, métricas, repetidas, concorrentes_cols, polos_cols):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Relatorio de Unidades Negativas", ln=True, align='C')
    pdf.ln(10)
    
    # Métricas Gerais
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Resumo Executivo", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(200, 7, f"Lojas Analisadas: {métricas['qtd']}", ln=True)
    pdf.cell(200, 7, f"Prejuizo Total Mes: R$ {métricas['prej_mes']:,.2f}", ln=True)
    pdf.cell(200, 7, f"Prejuizo Acumulado: R$ {métricas['prej_acum']:,.2f}", ln=True)
    pdf.cell(200, 7, f"Media % Aluguel: {métricas['avg_aluguel']:.2f}%", ln=True)
    pdf.ln(10)

    # Detalhamento por Loja
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, "Analise Individual de Unidades", ln=True)
    pdf.ln(5)

    for _, row in df.sort_values(by='RO Mês').iterrows():
        # Cabeçalho da Loja
        pdf.set_font("Arial", 'B', 10)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(0, 8, f"Unidade: {row['Desc_CC']}", ln=True, fill=True)
        
        # Financeiro
        pdf.set_font("Arial", '', 9)
        info_fin = f"RO Mes: R$ {row['RO Mês']:,.2f} | RO Acum: R$ {row['RO Acum']:,.2f} | Aluguel: R$ {row['Aluguel Mês']:,.2f} ({row['%Aluguel Mês']:.1f}%)"
        pdf.cell(0, 7, info_fin, ln=True)
        
        # Concorrência e Polos
        conc = [c for c in concorrentes_cols if str(row[c]).lower() in ['sim', 'x', 's', '1', '1.0']]
        polos = [p for p in polos_cols if str(row[p]).lower() in ['sim', 'x', 's', '1', '1.0']]
        
        pdf.cell(0, 7, f"Concorrentes: {', '.join(conc) if conc else 'Nenhum'}", ln=True)
        pdf.cell(0, 7, f"Polos Proximos: {', '.join(polos) if polos else 'Nenhum'}", ln=True)
        pdf.ln(3)
        
        if pdf.get_y() > 250: # Evita quebrar no fim da página
            pdf.add_page()

    return pdf.output(dest='S').encode('latin-1', 'replace')

# 2. PROJEÇÃO DE CRESCIMENTO (SEÇÃO 1)
# [Mantido conforme seu original...]
st.sidebar.header("1. Parâmetros de Projeção")
arquivo_subido = st.sidebar.file_uploader("Taxas de Crescimento:", type=["xlsx", "xls", "csv"], key="proj_file")
taxas = []
if arquivo_subido is not None:
    try:
        if "csv" in arquivo_subido.name.lower():
            df_growth = pd.read_csv(arquivo_subido, decimal=',', engine='python')
        else:
            df_growth = pd.read_excel(arquivo_subido)
        df_growth = df_growth.dropna(axis=1, how='all')
        valor_estudo = st.sidebar.number_input("Venda Alvo (Meta 100%):", min_value=0.0, value=400000.0, step=10000.0)
        estados_alvo = ["RS", "SC", "PR"]
        estado_sel = st.sidebar.selectbox("Estado Base:", estados_alvo)
        cols_matching = [c for c in df_growth.columns if estado_sel in str(c)]
        if cols_matching:
            col_nome_real = cols_matching[-1] 
            taxas = pd.to_numeric(df_growth[col_nome_real], errors='coerce').fillna(0).values
            projecao = []
            percentual_inicial = 0.77 if estado_sel == "RS" else 0.60
            valor_atual = valor_estudo * percentual_inicial
            projecao.append(valor_atual)
            for i in range(1, 36):
                if i < len(taxas):
                    taxa_mes = taxas[i]
                    valor_atual = valor_atual * (1 + taxa_mes)
                    projecao.append(valor_atual)
            df_res = pd.DataFrame({"Mês": range(1, len(projecao) + 1), "Faturamento": projecao})
            df_res["% Maturação"] = (df_res["Faturamento"] / valor_estudo) * 100
            c1, c2 = st.columns([2, 1])
            with c1:
                fig = px.line(df_res, x="Mês", y="Faturamento", markers=True, title=f"Curva de Maturação Esperada - {estado_sel}", template="plotly_white", color_discrete_sequence=["#00CC96"])
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                st.subheader("Tabela de Evolução")
                st.dataframe(df_res.style.format({"Faturamento": "R$ {:,.2f}", "% Maturação": "{:.2f}%"}), height=400, use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Erro na projeção: {e}")

# 3. COMPARATIVO REAL (SEÇÃO 2)
# [Mantido conforme seu original...]
st.markdown("---")
st.sidebar.header("2. Dados Históricos")
arquivo_historico = st.sidebar.file_uploader("Histórico de Vendas:", type=["xlsx", "xls", "csv"], key="hist_file")
if arquivo_historico:
    try:
        df_hist = pd.read_csv(arquivo_historico, decimal='.', engine='python') if "csv" in arquivo_historico.name.lower() else pd.read_excel(arquivo_historico)
        if 'Desc_Filial' in df_hist.columns:
            filiais = sorted(df_hist['Desc_Filial'].unique())
            filial_sel = st.selectbox("Filial para comparação:", filiais)
            df_loja = df_hist[df_hist['Desc_Filial'] == filial_sel].copy().sort_values(by='AnoMes')
            venda_inicial_real = df_loja['Mercadoria'].iloc[0]
            esperado = [venda_inicial_real]
            for i in range(1, len(df_loja)):
                esperado.append(esperado[-1] * (1 + taxas[i]) if len(taxas) > i else esperado[-1])
            df_loja['Crescimento_Esperado'] = esperado
            fig_hist = px.bar(df_loja, x='AnoMes', y='Mercadoria', title=f"Realizado vs Projetado: {filial_sel}", template="plotly_white")
            fig_hist.add_scatter(x=df_loja['AnoMes'], y=df_loja['Crescimento_Esperado'], mode='lines+markers', name='Projeção')
            st.plotly_chart(fig_hist, use_container_width=True)
    except Exception as e:
        st.error(f"Erro histórico: {e}")

# --- SEÇÃO 3: ANÁLISE DE LOJAS NEGATIVAS (COM PDF) ---
st.markdown("---")
st.header("Análise Estratégica: Performance de Unidades Negativas")
st.sidebar.header("3. Unidades Negativas")

arquivo_negativas = st.sidebar.file_uploader("Planilha de Lojas Negativas:", type=["xlsx", "xls"], key="negativas_file")

if arquivo_negativas:
    try:
        df = load_data_negativas(arquivo_negativas)
        
        # Métricas
        m_data = {
            'prej_mes': df['RO Mês'].sum(),
            'prej_acum': df['RO Acum'].sum(),
            'qtd': len(df),
            'avg_aluguel': df['%Aluguel Mês'].mean()
        }

        c0, c1, c2, c3 = st.columns(4)
        c0.metric("Lojas Analisadas", f"{m_data['qtd']}")
        c1.metric("Prejuízo Total Mês", f"R$ {m_data['prej_mes']:,.2f}")
        c2.metric("Prejuízo Acumulado", f"R$ {m_data['prej_acum']:,.2f}")
        c3.metric("Média % Aluguel", f"{m_data['avg_aluguel']:.2f}%")

        # Botão para PDF
        polos_lista = ["Aliment", "Ensin", "Saúd", "Banco", "Bem-est"]
        cols_polos = [c for c in df.columns if any(p.lower() in c.lower() for p in polos_lista)]
        concorrentes_lista = ["SaoJoao", "Independente", "Panvel", "Raia", "Morifarma", "Nissei", "PPCatarinense", "Pacheco", "FarmTrabalhador"]
        cols_conc = [c for c in df.columns if any(conc.lower() in c.lower() for conc in concorrentes_lista)]
        
        pdf_bytes = gerar_pdf_negativas(df, m_data, [], cols_conc, cols_polos)
        st.download_button(label="📥 Baixar Relatório PDF de Lojas Negativas", data=pdf_bytes, file_name="relatorio_lojas_negativas.pdf", mime="application/pdf")

        # Visualizações de tela (Gráficos)
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.subheader("Top 10 Unidades Críticas (Mês)")
            top_negativas = df.nsmallest(10, 'RO Mês')
            st.plotly_chart(px.bar(top_negativas, x='RO Mês', y='Desc_CC', orientation='h', color='RO Mês', color_continuous_scale='Reds_r'), use_container_width=True)
        with col_graf2:
            st.subheader("Aluguel vs Resultado (Mês)")
            st.plotly_chart(px.scatter(df, x='%Aluguel Mês', y='RO Mês', hover_name='Desc_CC', size='Aluguel Mês'), use_container_width=True)

        # Listagem Detalhada em Cards na Tela
        st.markdown("### Detalhamento por Unidade")
        cols_cards = st.columns(3)
        for idx, (_, row) in enumerate(df.sort_values(by='RO Mês').iterrows()):
            with cols_cards[idx % 3]:
                st.warning(f"**{row['Desc_CC']}**\n\nRO: R$ {row['RO Mês']:,.2f}\n\nAluguel: R$ {row['Aluguel Mês']:,.2f}")

    except Exception as e:
        st.error(f"Erro processamento negativas: {e}")

# 4. ANÁLISE FINANCEIRA (DRE) (SEÇÃO 4)
# [Mantido conforme seu original...]
st.markdown("---")
st.header("Análise de DRE e Rentabilidade")
arquivos_dre = st.sidebar.file_uploader("Upload DREs:", type=["xlsx", "xls", "csv"], key="dre_file_upload", accept_multiple_files=True)
if arquivos_dre:
    for arquivo_dre in arquivos_dre:
        try:
            st.markdown(f"### Unidade: {arquivo_dre.name}")
            # ... [Lógica de processamento DRE mantida]
        except Exception as e:
            st.error(f"Erro no DRE {arquivo_dre.name}: {e}")
