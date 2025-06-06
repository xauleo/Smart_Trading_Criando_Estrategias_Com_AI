import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os

class DataCollector:
    def __init__(self):
        """Inicializa o coletor de dados do MetaTrader 5"""
        if not mt5.initialize():
            print("Falha ao inicializar o MetaTrader 5")
            mt5.shutdown()
            raise Exception("Erro na inicialização do MT5")
        
        # Configuração do timezone
        self.timezone = pytz.timezone("America/Sao_Paulo")
        
    def __del__(self):
        """Fecha a conexão com o MetaTrader 5"""
        mt5.shutdown()
    
    def get_historical_data(self, symbol, timeframe, start_date, end_date=None):
        """
        Obtém dados históricos do MetaTrader 5
        
        Args:
            symbol (str): Símbolo do ativo (ex: "GBPUSD")
            timeframe (str): Timeframe dos dados ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
            start_date (datetime): Data inicial
            end_date (datetime, optional): Data final. Se None, usa a data atual
            
        Returns:
            pandas.DataFrame: DataFrame com os dados históricos
        """
        # Mapeamento de timeframes
        timeframe_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        if timeframe not in timeframe_map:
            raise ValueError(f"Timeframe inválido. Use um dos seguintes: {list(timeframe_map.keys())}")
        
        # Se end_date não for fornecido, usa a data atual
        if end_date is None:
            end_date = datetime.now(self.timezone)
        
        # Converte as datas para o formato do MT5
        start_date = start_date.astimezone(self.timezone)
        end_date = end_date.astimezone(self.timezone)
        
        # Obtém os dados históricos
        rates = mt5.copy_rates_range(
            symbol,
            timeframe_map[timeframe],
            start_date,
            end_date
        )
        
        if rates is None:
            raise Exception(f"Erro ao obter dados para {symbol}")
        
        # Converte para DataFrame
        df = pd.DataFrame(rates)
        
        # Converte o timestamp para datetime
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Renomeia as colunas para português
        df = df.rename(columns={
            'time': 'datetime',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'tick_volume': 'Volume',
            'spread': 'Spread',
            'real_volume': 'RealVolume'
        })
        
        return df
    
    def save_historical_data(self, symbol, timeframe, start_date, end_date=None, filename=None):
        """
        Salva dados históricos em um arquivo CSV
        
        Args:
            symbol (str): Símbolo do ativo
            timeframe (str): Timeframe dos dados
            start_date (datetime): Data inicial
            end_date (datetime, optional): Data final
            filename (str, optional): Nome do arquivo. Se None, usa formato padrão
        """
        # Obtém os dados
        df = self.get_historical_data(symbol, timeframe, start_date, end_date)
        
        # Define o nome do arquivo se não fornecido
        if filename is None:
            filename = f"{symbol}_{timeframe}.csv"
        
        # Cria o diretório data se não existir
        os.makedirs('data', exist_ok=True)
        
        # Salva o arquivo
        filepath = os.path.join('data', filename)
        df.to_csv(filepath, index=False)
        print(f"Dados salvos em: {filepath}")
        
        return filepath
    
    def get_current_price(self, symbol):
        """
        Obtém o preço atual de um ativo
        
        Args:
            symbol (str): Símbolo do ativo
            
        Returns:
            float: Preço atual do ativo
        """
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise Exception(f"Erro ao obter preço atual para {symbol}")
        return tick.last
    
    def get_available_symbols(self):
        """
        Obtém lista de símbolos disponíveis
        
        Returns:
            list: Lista de símbolos disponíveis
        """
        symbols = mt5.symbols_get()
        if symbols is None:
            raise Exception("Erro ao obter lista de símbolos")
        return [symbol.name for symbol in symbols]

# Exemplo de uso
if __name__ == "__main__":
    try:
        # Inicializa o coletor
        collector = DataCollector()
        
        # Obtém dados históricos do GBPUSD nos últimos 7 dias
        end_date = datetime.now()
        start_date = end_date - timedelta(days=490)
        
        # Salva os dados em CSV
        filepath = collector.save_historical_data(
            symbol="GBPUSD",
            timeframe="M15",
            start_date=start_date,
            end_date=end_date,
            filename="GBPUSD_15m.csv"
        )
        
        print(f"\nDados salvos em: {filepath}")
        
        # Obtém preço atual
        current_price = collector.get_current_price("GBPUSD")
        print(f"\nPreço atual do GBPUSD: {current_price}")
        
        # Lista símbolos disponíveis
        symbols = collector.get_available_symbols()
        print("\nSímbolos disponíveis:")
        print(symbols[:10])  # Mostra os 10 primeiros símbolos
        
    except Exception as e:
        print(f"Erro: {e}")