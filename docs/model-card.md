# Modelo e protocolo de avaliação

O alvo é a quantidade de aluguéis em cada dia. A unidade da previsão é a mesma do alvo, e os valores podem ser fracionários porque são estimativas de demanda. A API prevê os dias que vêm depois da última observação do artefato; não consulta a data atual do computador.

## Entradas disponíveis na origem da previsão

O modelo usa posição no calendário, codificações cíclicas do dia da semana e do ano, lags de 1/7/14 dias, média de 7/28 dias e desvio padrão de 7 dias. O cálculo das médias usa apenas dias estritamente anteriores ao alvo. Não usamos `casual` e `registered` da UCI nem temperatura observada no dia que queremos prever.

## Treinamento e previsão

O estimador é `HistGradientBoostingRegressor`, com parâmetros fixos no código e seed 42. O treino usa todas as observações disponíveis, descontados os primeiros 28 dias necessários aos lags. O modelo armazena os últimos 28 valores, a origem do calendário e a data final do treino. Não faz atualização automática com as respostas da API.

A previsão é recursiva: o resultado do primeiro dia entra no histórico necessário ao segundo, e assim por diante, até 28 dias. Erros podem acumular. Não fornecemos intervalos de confiança nem probabilidade calibrada.

## Avaliação

O backtest utiliza janela de treino crescente e holdouts consecutivos. No padrão, são três folds com 28 dias de teste cada. Cada fold treina do zero; a previsão dos 28 dias usa somente os dados anteriores à origem daquele fold. Nenhum valor observado durante o holdout alimenta os lags da própria previsão. Dados de um fold passado podem entrar no treino do fold seguinte, reproduzindo um retreino em uma data posterior.

A comparação é a previsão sazonal ingênua: repetir os sete últimos dias, também de forma recursiva. A avaliação calcula MAE e RMSE em todos os pontos previstos, e a variação percentual de MAE em relação ao baseline. Uma variação negativa significa que o modelo perdeu. Os parâmetros não foram escolhidos por busca sobre esses folds; qualquer ajuste futuro deve reservar outro período de teste.

## Limitações e operação

- A base sintética é um teste funcional. A base UCI é histórica e de uma única cidade; não demonstra desempenho em outras localidades.
- Não há feriados locais, promoções ou previsão meteorológica. Mudanças de operação exigem reavaliação.
- A API guarda um modelo por processo. Para trocar o artefato, finalize o treino e reinicie o serviço. O arquivo é escrito por substituição para evitar um artefato parcialmente escrito.
- `joblib` utiliza pickle. O caminho de artefato é configuração administrativa, não entrada de upload. Carregue apenas arquivos produzidos em um diretório confiável.
- `/health` é liveness e informa se há arquivo. `/model` valida o carregamento; sem artefato válido, ele e `/forecast` retornam 503.
- A API local não inclui autenticação. Restrinja o acesso ou coloque um gateway com autenticação antes de expô-la publicamente.

