taxas_estado = (
    df_growth
    .filter(regex=f"^{estado_sel}$|{estado_sel}", axis=1)
    .iloc[:,0]
    .fillna(0)
    .astype(float)
    .tolist()
)

projecao = []
valor_atual = valor_estudo * percentual_inicial

for taxa in taxas_estado:
    projecao.append(valor_atual)
    valor_atual *= (1 + taxa)
