import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import pytz

class ColetorDados:
    def __init__(self):
        """Inicializa o coletor de dados do MetaTrader 5"""
        if not mt5.initialize():
            print("Falha ao inicializar o MetaTrader 5")
            mt5.shutdown()
            raise Exception("Erro na inicialização do MT5")
        
        # Configuração do fuso horário
        self.fuso_horario = pytz.timezone("America/Sao_Paulo")
        
    def __del__(self):
        """Fecha a conexão com o MetaTrader 5"""
        mt5.shutdown()
    
    def obter_dados_historicos(self, simbolo, periodo, data_inicial, data_final=None):
        """
        Obtém dados históricos do MetaTrader 5
        
        Args:
            simbolo (str): Símbolo do ativo (ex: "PETR4")
            periodo (str): Período dos dados ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
            data_inicial (datetime): Data inicial
            data_final (datetime, opcional): Data final. Se None, usa a data atual
            
        Returns:
            pandas.DataFrame: DataFrame com os dados históricos
        """
        # Mapeamento de períodos
        mapa_periodos = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        if periodo not in mapa_periodos:
            raise ValueError(f"Período inválido. Use um dos seguintes: {list(mapa_periodos.keys())}")
        
        # Se data_final não for fornecida, usa a data atual
        if data_final is None:
            data_final = datetime.now(self.fuso_horario)
        
        # Converte as datas para o formato do MT5
        data_inicial = data_inicial.astimezone(self.fuso_horario)
        data_final = data_final.astimezone(self.fuso_horario)
        
        # Obtém os dados históricos
        dados = mt5.copy_rates_range(
            simbolo,
            mapa_periodos[periodo],
            data_inicial,
            data_final
        )
        
        if dados is None:
            raise Exception(f"Erro ao obter dados para {simbolo}")
        
        # Converte para DataFrame
        df = pd.DataFrame(dados)
        
        # Converte o timestamp para datetime
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Renomeia as colunas para português
        df = df.rename(columns={
            'time': 'data',
            'open': 'abertura',
            'high': 'maxima',
            'low': 'minima',
            'close': 'fechamento',
            'tick_volume': 'volume',
            'spread': 'spread',
            'real_volume': 'volume_real'
        })
        
        return df
    
    def obter_preco_atual(self, simbolo):
        """
        Obtém o preço atual de um ativo
        
        Args:
            simbolo (str): Símbolo do ativo
            
        Returns:
            float: Preço atual do ativo
        """
        tick = mt5.symbol_info_tick(simbolo)
        if tick is None:
            raise Exception(f"Erro ao obter preço atual para {simbolo}")
        return tick.last
    
    def obter_simbolos_disponiveis(self):
        """
        Obtém lista de símbolos disponíveis
        
        Returns:
            list: Lista de símbolos disponíveis
        """
        simbolos = mt5.symbols_get()
        if simbolos is None:
            raise Exception("Erro ao obter lista de símbolos")
        return [simbolo.name for simbolo in simbolos]

# Exemplo de uso
if __name__ == "__main__":
    try:
        # Inicializa o coletor
        coletor = ColetorDados()
        
        # Obtém dados históricos do PETR4 nos últimos 7 dias
        data_final = datetime.now()
        data_inicial = data_final - timedelta(days=7)
        
        df = coletor.obter_dados_historicos(
            simbolo="PETR4",
            periodo="H1",
            data_inicial=data_inicial,
            data_final=data_final
        )
        
        print("\nDados históricos do PETR4:")
        print(df.head())
        
        # Obtém preço atual
        preco_atual = coletor.obter_preco_atual("PETR4")
        print(f"\nPreço atual do PETR4: {preco_atual}")
        
        # Lista símbolos disponíveis
        simbolos = coletor.obter_simbolos_disponiveis()
        print("\nSímbolos disponíveis:")
        print(simbolos[:10])  # Mostra os 10 primeiros símbolos
        
    except Exception as e:
        print(f"Erro: {e}") 