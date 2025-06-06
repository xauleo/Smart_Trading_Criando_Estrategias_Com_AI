import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, time, timedelta
from data import DataCollector

class VWAPStrategy(Strategy):
    # Parâmetros
    volume_period = 20  # Período para média de volume
    stop_loss = 0.01    # 1%
    take_profit = 0.01  # 1%
    max_trades_per_day = 3
    
    def init(self):
        # Calcula VWAP
        typical_price = (self.data.High + self.data.Low + self.data.Close) / 3
        volume = self.data.Volume
        
        # Calcula VWAP usando uma janela móvel
        def calculate_vwap():
            vwap = np.zeros_like(self.data.Close)
            for i in range(len(self.data)):
                if i == 0:
                    vwap[i] = typical_price[i]
                else:
                    vwap[i] = (vwap[i-1] * volume[i-1] + typical_price[i] * volume[i]) / (volume[i-1] + volume[i])
            return vwap
        
        # Calcula média de volume
        def calculate_volume_ma():
            volume_ma = np.zeros_like(self.data.Volume)
            for i in range(len(self.data)):
                if i < self.volume_period:
                    volume_ma[i] = self.data.Volume[i]
                else:
                    volume_ma[i] = np.mean(self.data.Volume[i-self.volume_period:i])
            return volume_ma
        
        self.vwap = self.I(calculate_vwap)
        self.volume_ma = self.I(calculate_volume_ma)
        
        # Para rastrear trades do dia
        self.trades_today = 0
        self.last_trade_date = None
    
    def next(self):
        # Verifica se é um novo dia
        current_date = self.data.index[-1].date()
        if self.last_trade_date != current_date:
            self.trades_today = 0
            self.last_trade_date = current_date
        
        # Se já atingiu o limite de trades do dia, não faz nada
        if self.trades_today >= self.max_trades_per_day:
            return
        
        # Obtém valores atuais
        current_close = self.data.Close[-1]
        current_volume = self.data.Volume[-1]
        current_vwap = self.vwap[-1]
        avg_volume = self.volume_ma[-1]
        
        # Lógica de trading
        if not self.position:  # Se não há posição aberta
            # Sinal de compra: fechamento acima da VWAP e volume maior que a média
            if current_close > current_vwap and current_volume > avg_volume:
                self.buy(sl=current_close * (1 - self.stop_loss),
                        tp=current_close * (1 + self.take_profit))
                self.trades_today += 1
            
            # Sinal de venda: fechamento abaixo da VWAP e volume maior que a média
            elif current_close < current_vwap and current_volume > avg_volume:
                self.sell(sl=current_close * (1 + self.stop_loss),
                         tp=current_close * (1 - self.take_profit))
                self.trades_today += 1

# Obtém os dados usando o DataCollector
print("📥 Obtendo dados do EURUSD...")
collector = DataCollector()

# Define o período de dados (desde o início de 2024 até hoje)
end_date = datetime.now()
start_date = datetime(2024, 1, 1)

# Obtém os dados históricos
data = collector.get_historical_data(
    symbol="EURUSD",
    timeframe="M15",
    start_date=start_date,
    end_date=end_date
)

# Configura o índice datetime
data.set_index('datetime', inplace=True)

print(f"\n📅 Período do Backtest: {data.index[0].strftime('%Y-%m-%d')} até {data.index[-1].strftime('%Y-%m-%d')}")
print(f"📊 Total de candles: {len(data)}")

# Cria e configura o backtest
bt = Backtest(data, VWAPStrategy, cash=1000, commission=0.0001)  # Commission típica para forex

# Executa o backtest com parâmetros padrão
print("\n🌟 BACKTEST VWAP EURUSD INICIANDO - Parâmetros Padrão 🌟")
stats_default = bt.run()
print("\n📊 RESULTADOS DOS PARÂMETROS PADRÃO:")
print(stats_default)

# Realiza a otimização
print("\n🔍 OTIMIZAÇÃO INICIANDO - Isso pode demorar um pouco... 🔍")
optimization_results = bt.optimize(
    volume_period=range(10, 31, 5),  # Testa períodos de 10 a 30 para média de volume
    stop_loss=[i/100 for i in range(5, 16, 5)],  # Testa SL de 0.5% a 1.5%
    take_profit=[i/100 for i in range(5, 16, 5)],  # Testa TP de 0.5% a 1.5%
    max_trades_per_day=range(2, 5),  # Testa 2 a 4 trades por dia
    maximize='Equity Final [$]',
    constraint=lambda param: param.stop_loss > 0 and param.take_profit > 0  # Garante parâmetros válidos
)

# Imprime os resultados da otimização
print("\n🏆 OTIMIZAÇÃO CONCLUÍDA - Resultados:")
print(optimization_results)

# Imprime os melhores valores otimizados
print("\n✨ MELHORES PARÂMETROS:")
print(f"Período de Volume: {optimization_results._strategy.volume_period}")
print(f"Stop Loss: {optimization_results._strategy.stop_loss * 100:.1f}%")
print(f"Take Profit: {optimization_results._strategy.take_profit * 100:.1f}%")
print(f"Trades Máximos por Dia: {optimization_results._strategy.max_trades_per_day}")

# Plota o gráfico do backtest com os parâmetros otimizados
try:
    bt.plot()
except Exception as e:
    print(f"\n⚠️ Erro ao plotar o gráfico: {e}")
    print("Os resultados do backtest ainda estão disponíveis acima.")