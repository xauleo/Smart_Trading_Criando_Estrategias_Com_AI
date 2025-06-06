import pandas as pd
import numpy as np
from backtesting import Backtest, Strategy
from datetime import datetime, time

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
        
        # Calcula VWAP usando rolling window
        self.vwap = self.I(lambda: (typical_price * volume).rolling(window=len(self.data)).sum() / 
                          volume.rolling(window=len(self.data)).sum())
        
        # Calcula média de volume dos últimos 20 períodos
        self.volume_ma = self.I(lambda: volume.rolling(window=self.volume_period).mean())
        
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

# Carrega os dados do EURUSD
data_path = 'data/EURUSD_15m.csv'  # Ajuste o caminho conforme necessário
data = pd.read_csv(data_path, parse_dates=['datetime'], index_col='datetime')

# Renomeia colunas para corresponder ao formato esperado
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Cria e configura o backtest
bt = Backtest(data, VWAPStrategy, cash=100000, commission=0.0001)  # Ajuste commission conforme seu broker

# Executa o backtest
print("🌟 BACKTEST VWAP EURUSD INICIANDO 🌟")
stats = bt.run()
print("\n📊 RESULTADOS DO BACKTEST:")
print(stats)

# Plota o gráfico do backtest
bt.plot()