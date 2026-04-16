# --- SEÇÃO DRE ATUALIZADA: CHECKLIST DE METAS E OFENSORES ---
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
        df_dre_raw = pd.read_excel(arquivo_dre, header=None)
        
        # Mapeamento de Linhas (Coluna B)
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
            match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.strip().str.contains(texto, case=False, na=False)]
            if not match.empty:
                indices[chave] = match.index[0]

        def pegar_v(chave):
            if chave in indices:
                # Índice 3 é a coluna "Realizado Total" conforme a estrutura da imagem
                val = df_dre_raw.iloc[indices[chave], 3] 
                return pd.to_numeric(val, errors='coerce') if pd.notnull(val) else 0.0
            return 0.0

        vals = {k: pegar_v(k) for k in termos.keys()}
        rb = vals['RB'] if vals['RB'] > 0 else 1 # Evitar divisão por zero
        
        # Cálculo de Indicadores Reais
        perdas_totais = abs(vals['PVL']) + abs(vals['DISC'])
        p_margem = (vals['MC'] / rb) * 100
        p_perda  = (perdas_totais / rb) * 100
        p_folha  = (abs(vals['FOLHA']) / rb) * 100
        p_adm    = (abs(vals['ADM']) / rb) * 100
        p_oper   = (abs(vals['OPER']) / rb) * 100

        # 1. MÉTRICAS DE TOPO
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento", f"R$ {vals['RB']:,.2f}")
        m2.metric("Margem Real", f"{p_margem:.1f}%", delta="Meta: >30%")
        m3.metric("Resultado", f"R$ {vals['RES']:,.2f}", delta=f"{(vals['RES']/rb*100):.1f}%", delta_color="normal" if vals['RES'] > 0 else "inverse")
        m4.metric("Quebra Total", f"{p_perda:.2f}%", delta="Meta: <1.5%", delta_color="inverse")

        st.markdown("---")

        # 2. STATUS DAS ÁREAS (O QUE NÃO ESTÁ BATENDO)
        col_check, col_graf = st.columns([1.2, 1])
        
        with col_check:
            st.subheader("🚩 Status por Área (Meta vs Real)")
            
            # Função para exibir o status de forma limpa
            def check_meta(nome_area, valor_real, meta, invertido=False):
                if not invertido: # Para Margem/Resultado (Quanto maior, melhor)
                    sucesso = valor_real >= meta
                    simbolo = "✅" if sucesso else "❌"
                    cor = "green" if sucesso else "red"
                else: # Para Despesas/Perdas (Quanto menor, melhor)
                    sucesso = valor_real <= meta
                    simbolo = "✅" if sucesso else "❌"
                    cor = "green" if sucesso else "red"
                
                st.markdown(f"**{simbolo} {nome_area}:** {valor_real:.2f}% (Meta: {'<' if invertido else '>'} {meta}%)")

            # Execução do Checklist baseado nas imagens e metas de mercado
            check_meta("Margem de Contribuição", p_margem, 30.0)
            check_meta("Perdas e Discrepâncias", p_perda, 1.5, invertido=True)
            check_meta("Despesas de Folha", p_folha, 12.0, invertido=True)
            check_meta("Despesas ADM", p_adm, 5.0, invertido=True)
            check_meta("Despesas Operação", p_oper, 6.0, invertido=True)

            if vals['RES'] < 0:
                st.error(f"🚨 **Atenção:** A área de **Resultado Operacional** está negativa. A operação é deficitária em R$ {abs(vals['RES']):,.2f}.")

        with col_graf:
            # Gráfico comparativo de ofensores
            df_plot = pd.DataFrame({
                "Área": ["Margem", "Folha", "Operação", "ADM", "Quebra"],
                "Percentual %": [p_margem, p_folha, p_oper, p_adm, p_perda]
            })
            fig_bar = px.bar(df_plot, x="Área", y="Percentual %", text_auto='.1f',
                             title="Visão Percentual por Conta",
                             color="Área", color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig_bar, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao analisar áreas do DRE: {e}")
