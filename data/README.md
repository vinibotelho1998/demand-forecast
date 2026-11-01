# Dados e atribuição

`demo.csv` é uma série **sintética**, produzida pelo comando `demand-forecast demo --days 540 --seed 42`. Contém uma tendência, ciclos semanais/anuais e ruído. Serve para verificar o fluxo; seus resultados não estimam desempenho em uma operação real.

O comando `download-uci` baixa o arquivo oficial [Bike Sharing](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset), lê apenas `day.csv` e mantém `dteday` e `cnt`, renomeados para `date` e `demand`. A saída local `uci-day.csv` fica fora do Git. O modelo não recebe `casual` ou `registered`, que somam o alvo, nem clima observado no futuro.

A base contém contagens do sistema Capital Bikeshare em 2011–2012. A [página oficial](https://archive.ics.uci.edu/dataset/275/bike+sharing+dataset) informa a licença **CC BY 4.0**, consultada em 26/10/2026. Preserve essa atribuição ao compartilhar derivações.

Fanaee-T, H. (2013). *Bike Sharing* [Dataset]. UCI Machine Learning Repository. DOI: [10.24432/C5W894](https://doi.org/10.24432/C5W894).

Nenhum dado pessoal é necessário para rodar este projeto. Novos CSVs devem ter datas locais consecutivas e demanda finita, não negativa. Dias faltantes ou duplicados são rejeitados: o projeto exige uma decisão explícita de tratamento em vez de inventar demanda silenciosamente.

