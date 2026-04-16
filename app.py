# --- SEÇÃO FINAL: ANÁLISE DE DRE E DIAGNÓSTICO DE PERFORMANCE ---
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
        # Leitura da DRE (tratando cabeçalhos complexos comuns em DREs)
        if "csv" in arquivo_dre.name.lower():
            df_dre = pd.read_csv(arquivo_dre, engine='python')
        else:
            df_dre = pd.read_excel(arquivo_dre, header=1) # Pula a primeira linha vazia se houver

        # 1. Identificação de Linhas Críticas
        # Buscamos palavras-chave nas linhas para identificar os indicadores
        def localizar_valor(keyword):
            row = df_dre[df_dre.iloc[:, 1].astype(str).str.contains(keyword, case=False, na=False)]
            if not row.empty:
                # Pegamos o valor da coluna 'Total' ou a última coluna numérica
                return row.iloc[0]['Total'] if 'Total' in df_dre.columns else row.iloc[0, -1]
            return 0

        receita_bruta = localizar_valor("Receita Bruta")
        margem_contribuicao = localizar_valor("Margem de Contribuição")
        despesas_operacao = localizar_valor("Despesas Operação")
        resultado_liquido = localizar_valor("Lucro/Prejuízo") # Ou Resultado Líquido

        # 2. Exibição de Métricas Financeiras
        col_dre1, col_dre2, col_dre3, col_dre4 = st.columns(4)
        
        status_lucro = "Normal" if resultado_liquido >= 0 else "Inverse"
        col_dre1.metric("Receita Total", f"R$ {receita_bruta:,.2f}")
        col_dre2.metric("Margem Contrib.", f"R$ {margem_contribuicao:,.2f}")
        col_dre3.metric("Total Despesas", f"R$ {abs(despesas_operacao):,.2f}", delta_color="inverse")
        col_dre4.metric("Lucro Líquido", f"R$ {resultado_liquido:,.2f}", delta_color=status_lucro)

        # 3. ALGORITMO DE DIAGNÓSTICO
        st.subheader("🕵️ Análise do Especialista (AI)")
        
        diagnostico = []
        alertas = []

        # Cálculo de Eficiência
        perc_margem = (margem_contribuicao / receita_bruta) if receita_bruta > 0 else 0
        perc_despesa = (abs(despesas_operacao) / receita_bruta) if receita_bruta > 0 else 0

        if resultado_liquido < 0:
            diagnostico.append("🚨 **Atenção:** A loja está operando com **Resultado Negativo**. O faturamento atual não está cobrindo a estrutura de custos.")
            
            # Análise de Causas
            if perc_margem < 0.25: # Exemplo de threshold de 25%
                alertas.append("📉 **Margem Baixa:** A margem de contribuição está abaixo do esperado. Isso pode indicar excesso de promoções, furtos ou custo de mercadoria (CMV) muito alto.")
            
            if perc_despesa > 0.30:
                alertas.append("💸 **Despesas Elevadas:** As despesas operacionais estão consumindo mais de 30% da receita. Verifique gastos fixos, energia e folha de pagamento.")
        else:
            diagnostico.append("✅ **Operação Saudável:** A loja apresenta lucro líquido positivo no período analisado.")

        # Exibição do Diagnóstico em Box
        with st.container():
            st.info("\n\n".join(diagnostico))
            if alertas:
                for alerta in alertas:
                    st.warning(alerta)

        # 4. Detalhamento de Despesas (Visualização de Pareto)
        st.write("---")
        st.write("**Top Despesas que mais afetam o resultado:**")
        
        # Filtramos linhas que são despesas (negativas) e relevantes
        df_despesas = df_dre[df_dre.iloc[:, 1].astype(str).str.contains("Despesa|Gasto|Custo", case=False, na=False)].copy()
        # Pegamos o valor absoluto para o gráfico
        df_despesas['Valor_Abs'] = df_despesas.iloc[:, 3].apply(lambda x: abs(float(x)) if isinstance(x, (int, float)) else 0)
        df_despesas = df_despesas.sort_values(by='Valor_Abs', ascending=False).head(8)

        fig_dre = px.pie(df_despesas, values='Valor_Abs', names=df_despesas.columns[1], 
                         title="Distribuição das Maiores Despesas",
                         hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig_dre, use_container_width=True)

    except Exception as e:
        st.error(f"Erro ao processar DRE: Certifique-se que o arquivo segue o padrão de colunas da empresa.")
        st.info(f"Dica: O sistema busca pela coluna 'Total' e descrições na segunda coluna. Erro: {e}")
