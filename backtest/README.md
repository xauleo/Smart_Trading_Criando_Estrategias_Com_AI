# Backtest

## Visão Geral
O backtest é um componente crucial do sistema RBI (Pesquisa, Backtest, Implementação). Este processo envolve a análise de dados históricos de abertura, máxima, mínima, fechamento e volume para avaliar se uma estratégia de trading teria sido bem-sucedida no passado. Embora o desempenho passado não garanta resultados futuros, estratégias que funcionaram historicamente têm uma maior probabilidade de sucesso no futuro.

## Recursos

### Template
- **template.py**: Um template inicial para backtest que pode ser usado com qualquer ideia de trading. Este é projetado para funcionar com estratégias desenvolvidas na fase de pesquisa. Basta examinar o template e integrar sua estratégia pesquisada para ver como ela teria se desempenhado historicamente.

### Bibliotecas de Backtest
Este repositório inclui suporte para três bibliotecas populares de backtest:
1. **Backtesting.py**: Nossa biblioteca recomendada e a usada no arquivo template.py. Oferece um bom equilíbrio entre simplicidade e poder.
2. **Backtrader**: Um framework Python abrangente para backtest e trading.
3. **Zipline**: Um sistema de backtest orientado a eventos desenvolvido pela Quantopian.

### Aquisição de Dados
- **data.py**: Uma utilidade para obter dados de mercado do Yahoo Finance. Dados de qualidade são essenciais para um backtest eficaz - este módulo simplifica o processo de aquisição dos dados históricos necessários para testar suas estratégias.

## Começando
1. Revise sua ideia de trading da fase de pesquisa
2. Use data.py para coletar dados históricos de mercado
3. Modifique template.py para implementar sua estratégia
4. Execute o backtest e analise os resultados
5. Refine sua estratégia com base nas métricas de desempenho
