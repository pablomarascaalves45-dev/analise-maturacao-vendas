# --- SEÇÃO DRE CORRIGIDA: BUSCA DINÂMICA DE VALORES ---
st.markdown("---")
st.header("📋 Analisador de DRE: Diagnóstico de Rentabilidade")

st.sidebar.markdown("---")
st.sidebar.header("📁 Dados Financeiros (DRE)")
arquivo_dre = st.sidebar.file_uploader(
    "Suba a planilha de DRE (Excel/CSV):", 
    type=["xlsx", "xls", "csv"],
    key="dre_file"
)

if arquivo_dre is not None:
    try:
        # Carregamento robusto
        if "csv" in arquivo_dre.name.lower():
            df_dre_raw = pd.read_csv(arquivo_dre, header=None, sep=None, engine='python')
        else:
            df_dre_raw = pd.read_excel(arquivo_dre, header=None)
        
        # Mapeamento de Linhas (Coluna B / Índice 1)
        termos = {
            "RB": "Receita Bruta",
            "MC": "Margem de Contribuição",
            "PVL": "Perdas Vencidos Liquido",
            "DISC": "Discrepância _ Estoque",
            "FOLHA": "Despesas Folha",
            "ADM": "Despesas ADM",
            "OPER": "Despesas Operação",
            "RES": "Resultado Operacional"
        }

        indices = {}
        for chave, texto in termos.items():
            # Busca flexível que ignora espaços e maiúsculas/minúsculas
            match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.contains(texto, case=False, na=False)]
            if not match.empty:
                indices[chave] = match.index[0]

        def limpar_e_converter(valor):
            if pd.isna(valor): return 0.0
            if isinstance(valor, (int, float)): return float(valor)
            # Remove R$, pontos de milhar e troca vírgula por ponto
            s = str(valor).replace('R$', '').replace('.', '').replace(',', '.').strip()
            try:
                return float(s)
            except:
                return 0.0

        def pegar_valor_dinamico(chave):
            if chave in indices:
                linha_idx = indices[chave]
                # Varre da coluna 2 em diante até achar um número (evita cabeçalhos de texto)
                for col_idx in range(2, df_dre_raw.shape[1]):
                    val_bruto = df_dre_raw.iloc[linha_idx, col_idx]
                    num = limpar_e_converter(val_bruto)
                    if num != 0: # Assume que o primeiro número relevante é o Total
                        return num
            return 0.0

        vals = {k: pegar_valor_dinamico(k) for k in termos.keys()}
        rb = vals['RB'] if vals['RB'] != 0 else 1.0
        
        # Cálculo de Indicadores
        perdas_totais = abs(vals['PVL']) + abs(vals['DISC'])
        p_margem = (vals['MC'] / rb) * 100
        p_perda  = (perdas_totais / rb) * 100
        p_folha  = (abs(vals['FOLHA']) / rb) * 100
        p_adm    = (abs(vals['ADM']) / rb) * 100
        p_oper   = (abs(vals['OPER']) / rb) * 100

        # --- INTERFACE DE DIAGNÓSTICO ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento", f"R$ {vals['RB']:,.2f}")
        m2.metric("Margem Real", f"{p_margem:.1f}%", delta="Meta: >30%")
        m3.metric("Resultado", f"R$ {vals['RES']:,.2f}", delta=f"{(vals['RES']/rb*100):.1f}%")
        m4.metric("Quebra Total", f"{p_perda:.2f}%", delta="Meta: <1.5%", delta_color="inverse")

        st.markdown("---")
        col_check, col_graf = st.columns([1.2, 1])
        
        with col_check:
            st.subheader("🚩 Status por Área")
            
            # Checklist de Metas
            metrics = [
                ("Margem de Contribuição", p_margem, 30.0, False),
                ("Perdas e Discrepâncias", p_perda, 1.5, True),
                ("Despesas de Folha", p_folha, 12.0, True),
                ("Despesas ADM", p_adm, 5.0, True),
                ("Despesas Operação", p_oper, 6.0, True)
            ]

            for nome, valor, meta, invertido in metrics:
                sucesso = valor <= meta if invertido else valor >= meta
                simbolo = "✅" if sucesso else "❌"
                st.markdown(f"**{simbolo} {nome}:** {valor:.2f}% (Meta: {'<' if invertido else '>'} {meta}%)")

            if vals['RES'] < 0:
                st.error(f"🚨 **Resultado Operacional Crítico:** Prejuízo de R$ {abs(vals['RES']):,.2f}")

        with col_graf:
            df_plot = pd.DataFrame({
                "Área": ["Margem", "Folha", "Operação", "ADM", "Quebra"],
                "Percentual %": [p_margem, p_folha, p_oper, p_adm, p_perda]
            })
            fig_bar = px.bar(df_plot, x="Área", y="Percentual %", text_auto='.1f',
                             title="Análise Percentual",
                             color="Área", color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_bar, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar DRE: {e}. Verifique se o arquivo segue o padrão esperado.")
