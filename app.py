# --- SEÇÃO DRE CORRIGIDA: FILTRO DE STRINGS E BUSCA DE VALORES ---
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
        # Leitura flexível
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
            # Busca ignorando maiúsculas/minúsculas e espaços
            match = df_dre_raw[df_dre_raw.iloc[:, 1].astype(str).str.contains(texto, case=False, na=False)]
            if not match.empty:
                indices[chave] = match.index[0]

        def converter_apenas_numeros(valor):
            """Tenta converter para float. Se for texto (ex: 'Realizado'), retorna None."""
            if pd.isna(valor): return None
            try:
                # Se for string, limpa formatação de moeda/milhar
                if isinstance(valor, str):
                    s = valor.replace('R$', '').replace('.', '').replace(',', '.').strip()
                    return float(s)
                return float(valor)
            except ValueError:
                return None

        def pegar_valor_dinamico(chave):
            if chave in indices:
                linha_idx = indices[chave]
                # Varre as colunas a partir da C (índice 2) em diante
                for col_idx in range(2, df_dre_raw.shape[1]):
                    val_bruto = df_dre_raw.iloc[linha_idx, col_idx]
                    num = converter_apenas_numeros(val_bruto)
                    
                    # Só aceita se for um número válido e não for o cabeçalho
                    if num is not None:
                        return num
            return 0.0

        # Extração de valores com a nova lógica
        vals = {k: pegar_valor_dinamico(k) for k in termos.keys()}
        rb = vals['RB'] if vals['RB'] != 0 else 1.0
        
        # Cálculos de Performance
        perdas_totais = abs(vals['PVL']) + abs(vals['DISC'])
        p_margem = (vals['MC'] / rb) * 100
        p_perda  = (perdas_totais / rb) * 100
        p_folha  = (abs(vals['FOLHA']) / rb) * 100
        p_adm    = (abs(vals['ADM']) / rb) * 100
        p_oper   = (abs(vals['OPER']) / rb) * 100

        # --- EXIBIÇÃO DASHBOARD ---
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento", f"R$ {vals['RB']:,.2f}")
        m2.metric("Margem Real", f"{p_margem:.1f}%", delta="Meta: >30%")
        m3.metric("Resultado", f"R$ {vals['RES']:,.2f}", delta=f"{(vals['RES']/rb*100):.1f}%")
        m4.metric("Quebra Total", f"{p_perda:.2f}%", delta="Meta: <1.5%", delta_color="inverse")

        st.markdown("---")
        col_check, col_graf = st.columns([1.2, 1])
        
        with col_check:
            st.subheader("🚩 Status por Área (Checklist)")
            
            # Definição das Metas (Nome, Valor Atual, Meta, Se é Invertido [menor é melhor])
            areas_status = [
                ("Margem de Contribuição", p_margem, 30.0, False),
                ("Perdas e Discrepâncias", p_perda, 1.5, True),
                ("Despesas de Folha", p_folha, 12.0, True),
                ("Despesas ADM", p_adm, 5.0, True),
                ("Despesas Operação", p_oper, 6.0, True)
            ]

            for nome, valor, meta, invertido in areas_status:
                atingiu = valor <= meta if invertido else valor >= meta
                simbolo = "✅" if atingiu else "❌"
                st.markdown(f"**{simbolo} {nome}:** {valor:.2f}% (Meta: {'<' if invertido else '>'} {meta}%)")

            if vals['RES'] < 0:
                st.error(f"🚨 **Área Crítica:** Resultado Operacional negativo (Prejuízo).")

        with col_graf:
            df_plot = pd.DataFrame({
                "Área": ["Margem", "Folha", "Operação", "ADM", "Quebra"],
                "Percentual %": [p_margem, p_folha, p_oper, p_adm, p_perda]
            })
            fig_bar = px.bar(df_plot, x="Área", y="Percentual %", text_auto='.1f',
                             title="Análise de Ofensores (%)",
                             color="Área", color_discrete_sequence=px.colors.qualitative.Prism)
            st.plotly_chart(fig_bar, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar DRE: {e}")
