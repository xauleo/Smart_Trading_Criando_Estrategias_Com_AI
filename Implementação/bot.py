'''
🌙 Bot de Trading BB do XAUNOMAD 🚀
🎯 Estratégia de trading: Squeeze das Bandas de Bollinger com confirmação ADX
🔍 Detecta quando a volatilidade se contrai (squeeze BB) e negocia rompimentos
💥 Usa ADX para confirmar direção de tendência forte após liberação do squeeze

Construído com amor pelo XAUNOMAD 🌙 ✨
disclaimer: isso não é aconselhamento financeiro e não há garantia de qualquer tipo. use por sua conta e risco.
'''

import sys
import os
import time
import schedule
import json
import requests
import pandas as pd
import numpy as np
import traceback
import talib
from termcolor import colored
import colorama
from colorama import Fore, Back, Style
import nice_funcs as n
from datetime import datetime, timedelta
import pytz
from eth_account.signers.local import LocalAccount
import eth_account
from dotenv import load_dotenv

# Adiciona o diretório pai ao caminho Python para importar módulos de lá
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, parent_dir)

# Importa módulos locais
import nice_funcs as n

# Inicializa colorama para cores do terminal
colorama.init(autoreset=True)

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Obtém a chave Hyperliquid das variáveis de ambiente
HYPER_LIQUID_KEY = os.getenv('HYPER_LIQUID_KEY')

# Banner ASCII Arte do XAUNOMAD
XAUNOMAD_BANNER = f"""
{Fore.CYAN}
  ██╗  ██╗ █████╗ ██╗   ██╗███╗   ██╗ ██████╗ ███╗   ███╗ █████╗ ██████╗ 
  ╚██╗██╔╝██╔══██╗██║   ██║████╗  ██║██╔═══██╗████╗ ████║██╔══██╗██╔══██╗
   ╚███╔╝ ███████║██║   ██║██╔██╗ ██║██║   ██║██╔████╔██║███████║██║  ██║
   ██╔██╗ ██╔══██║██║   ██║██║╚██╗██║██║   ██║██║╚██╔╝██║██╔══██║██║  ██║
  ██╔╝ ██╗██║  ██║╚██████╔╝██║ ╚████║╚██████╔╝██║ ╚═╝ ██║██║  ██║██████╔╝
  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝╚═╝  ╚═╝╚═════╝ 

                             por LeonardoAlves
{Fore.RESET}
{Fore.MAGENTA}🚀 Bot de Trading VWAPEUR 🌙{Fore.RESET}
"""

# ===== CONFIGURAÇÃO =====
# Símbolo para negociar
SYMBOL = 'BTC'  # Símbolo padrão, pode ser alterado conforme necessário
LEVERAGE = 5     # Alavancagem para usar no trading
POSITION_SIZE_USD = 10  # Tamanho da posição em USD (pequeno para garantir performance como backtest)

# Parâmetros da estratégia (otimização do backtest)
BB_WINDOW = 20
BB_STD = 2.0
KELTNER_WINDOW = 20
KELTNER_ATR_MULT = 1.5
ADX_PERIOD = 14
ADX_THRESHOLD = 25

# Configurações de take profit e stop loss
TAKE_PROFIT_PERCENT = 5.0  # 5% - do backtest
STOP_LOSS_PERCENT = -3.0   # 3% - do backtest

# Tipo de ordem de mercado
USE_MARKET_ORDERS = False  # False para ordens limitadas, True para ordens de mercado

# Inicializa conta
account = LocalAccount = eth_account.Account.from_key(HYPER_LIQUID_KEY)

# Estado do trading
squeeze_flag = False  # Rastreia se estamos em um squeeze
squeeze_released = False  # Rastreia se um squeeze foi liberado recentemente
last_candle_time = None  # Rastreia quando processamos um candle pela última vez

def print_banner():
    """Imprime banner do XAUNOMAD com uma citação aleatória"""
    print(XAUNOMAD_BANNER)
    print(f"{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}🚀 Bot BB Squeeze ADX do XAUNOMAD está iniciando! 🎯")
    print(f"{Fore.YELLOW}💰 Negociando {SYMBOL} com alavancagem {LEVERAGE}x")
    print(f"{Fore.YELLOW}💵 Tamanho da posição: ${POSITION_SIZE_USD} USD")
    print(f"{Fore.CYAN}{'='*80}\n")

def fetch_klines(symbol, interval='4h', limit=100):
    """
    Busca dados de candlestick para o símbolo dado
    """
    print(f"{Fore.YELLOW}🔍 XAUNOMAD está buscando candles de {interval} para {symbol}... 🕯️")
    try:
        # Esta função seria implementada em nice_funcs
        ohlcv = n.get_ohlcv2(symbol, interval, limit)
        
        if ohlcv is None or len(ohlcv) == 0:
            print(f"{Fore.RED}❌ Falha ao buscar dados de candle!")
            return None
            
        # Converte para DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        print(f"{Fore.GREEN}✅ Buscou com sucesso {len(df)} candles para {symbol}")
        return df
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erro ao buscar candles: {str(e)}")
        print(f"{Fore.RED}📋 Rastreamento de pilha:\n{traceback.format_exc()}")
        return None

def calculate_indicators(df):
    """
    Calcula todos os indicadores da estratégia:
    - Bandas de Bollinger
    - Canais de Keltner
    - ADX
    """
    try:
        print(f"{Fore.YELLOW}🧮 XAUNOMAD calculando indicadores... 🧠")
        
        # Calcula Bandas de Bollinger
        df['upper_bb'], df['middle_bb'], df['lower_bb'] = talib.BBANDS(
            df['close'], 
            timeperiod=BB_WINDOW, 
            nbdevup=BB_STD, 
            nbdevdn=BB_STD
        )
        
        # Calcula ATR para Canais de Keltner
        df['atr'] = talib.ATR(
            df['high'], 
            df['low'], 
            df['close'], 
            timeperiod=KELTNER_WINDOW
        )
        
        # Calcula Canais de Keltner
        df['keltner_middle'] = talib.SMA(df['close'], timeperiod=KELTNER_WINDOW)
        df['upper_kc'] = df['keltner_middle'] + KELTNER_ATR_MULT * df['atr']
        df['lower_kc'] = df['keltner_middle'] - KELTNER_ATR_MULT * df['atr']
        
        # Calcula ADX
        df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=ADX_PERIOD)
        
        # Detecta Squeeze das Bandas de Bollinger
        df['squeeze'] = (df['upper_bb'] < df['upper_kc']) & (df['lower_bb'] > df['lower_kc'])
        
        print(f"{Fore.GREEN}✅ XAUNOMAD terminou de calcular indicadores! 🧙‍♂️")
        
        return df
    
    except Exception as e:
        print(f"{Fore.RED}❌ Erro ao calcular indicadores: {str(e)}")
        print(f"{Fore.RED}📋 Rastreamento de pilha:\n{traceback.format_exc()}")
        return None

def analyze_market():
    """
    Analisa condições de mercado e detecta padrões de squeeze BB
    """
    global squeeze_flag, squeeze_released
    
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{'='*25} 🔍 ANÁLISE DE MERCADO 🔍 {'='*25}")
    print(f"{Fore.CYAN}{'='*80}")
    
    try:
        # Busca dados de candle
        df = fetch_klines(SYMBOL, interval='6h', limit=100)
        if df is None:
            return False
        
        # Calcula indicadores
        df = calculate_indicators(df)
        if df is None:
            return False
        
        # Obtém os pontos de dados mais recentes
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        
        # Imprime preço atual e valores dos indicadores
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.CYAN}{'='*25} 📊 STATUS ATUAL DO MERCADO 📊 {'='*25}")
        print(f"{Fore.CYAN}{'='*80}")
        print(f"{Fore.GREEN}🕯️ Fechamento Atual: ${current_candle['close']:.2f}")
        print(f"{Fore.GREEN}📈 Valor ADX: {current_candle['adx']:.2f} (Limite: {ADX_THRESHOLD})")
        print(f"{Fore.GREEN}📏 Bandas de Bollinger: Superior ${current_candle['upper_bb']:.2f} | Médio ${current_candle['middle_bb']:.2f} | Inferior ${current_candle['lower_bb']:.2f}")
        print(f"{Fore.GREEN}📏 Canais de Keltner: Superior ${current_candle['upper_kc']:.2f} | Médio ${current_candle['keltner_middle']:.2f} | Inferior ${current_candle['lower_kc']:.2f}")
        
        # Verifica se estamos em um squeeze
        squeeze_now = current_candle['squeeze']
        squeeze_prev = previous_candle['squeeze']
        
        # Verifica se o squeeze terminou (era True, agora False)
        if squeeze_prev and not squeeze_now:
            print(f"\n{Fore.MAGENTA}🚨 ALERTA XAUNOMAD: SQUEEZE BB ACABOU DE SER LIBERADO! 🚨")
            squeeze_released = True
            squeeze_flag = False
        elif squeeze_now:
            print(f"\n{Fore.YELLOW}⚠️ ALERTA XAUNOMAD: Atualmente em Squeeze BB! Contração de volatilidade em progresso...")
            squeeze_flag = True
            squeeze_released = False
        else:
            print(f"\n{Fore.BLUE}ℹ️ INFO XAUNOMAD: Nenhum squeeze detectado. Volatilidade normal.")
            squeeze_flag = False
        
        # Exibe força da tendência ADX
        if current_candle['adx'] > ADX_THRESHOLD:
            print(f"{Fore.GREEN}💪 ADX: {current_candle['adx']:.2f} - Tendência forte detectada! (Limite: {ADX_THRESHOLD})")
        else:
            print(f"{Fore.YELLOW}👀 ADX: {current_candle['adx']:.2f} - Tendência fraca/sem tendência (Limite: {ADX_THRESHOLD})")
        
        # Verifica direção potencial de rompimento
        if squeeze_released:
            if current_candle['close'] > current_candle['upper_bb']:
                print(f"{Fore.GREEN}🚀 ROMPIMENTO POTENCIAL PARA CIMA - Fechamento (${current_candle['close']:.2f}) acima BB superior (${current_candle['upper_bb']:.2f})")
            elif current_candle['close'] < current_candle['lower_bb']:
                print(f"{Fore.RED}📉 ROMPIMENTO POTENCIAL PARA BAIXO - Fechamento (${current_candle['close']:.2f}) abaixo BB inferior (${current_candle['lower_bb']:.2f})")
        
        return True
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erro durante análise de mercado: {str(e)}")
        print(f"{Fore.RED}📋 Rastreamento de pilha:\n{traceback.format_exc()}")
        return False

def check_for_entry_signals(df):
    """
    Verifica sinais de entrada de trade baseados no squeeze BB e ADX
    """
    try:
        # Obtém últimos dois candles
        current = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Inicializa variáveis de sinal
        long_signal = False
        short_signal = False
        
        # Verifica se o squeeze acabou de terminar (estava em squeeze e agora não está)
        squeeze_just_released = previous['squeeze'] and not current['squeeze']
        
        # Se squeeze acabou de ser liberado e ADX confirma força da tendência
        if squeeze_just_released and current['adx'] > ADX_THRESHOLD:
            print(f"{Fore.MAGENTA}🔎 ANÁLISE DE SINAL XAUNOMAD: Squeeze acabou de ser liberado com ADX: {current['adx']:.2f} > {ADX_THRESHOLD} 💪")
            
            # Determina direção do rompimento
            if current['close'] > current['upper_bb']:
                long_signal = True
                print(f"{Fore.GREEN}🚀 SINAL LONG ATIVADO! Preço rompeu acima BB superior (${current['upper_bb']:.2f})")
                
            elif current['close'] < current['lower_bb']:
                short_signal = True
                print(f"{Fore.RED}📉 SINAL SHORT ATIVADO! Preço rompeu abaixo BB inferior (${current['lower_bb']:.2f})")
        
        return long_signal, short_signal
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erro ao verificar sinais de entrada: {str(e)}")
        print(f"{Fore.RED}📋 Rastreamento de pilha:\n{traceback.format_exc()}")
        return False, False

def bot():
    """
    Função principal do bot que executa a cada ciclo
    """
    try:
        print(f"\n{Fore.CYAN}{'='*80}")
        print(f"{Fore.YELLOW}🌙 Bot BB Squeeze ADX do XAUNOMAD - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 🚀")
        print(f"{Fore.CYAN}{'='*80}")
        
        # Primeiro verifica posições existentes e as gerencia
        print(f"\n{Fore.CYAN}🔍 Verificando posições existentes...")
        positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(SYMBOL, account)
        print(f"{Fore.CYAN}📊 Posições atuais: {positions}")
        
        if im_in_pos:
            print(f"{Fore.GREEN}📈 Em posição, verificando PnL para condições de fechamento...")
            print(f"{Fore.YELLOW}💰 PnL Atual: {pnl_perc:.2f}% | Take Profit: {TAKE_PROFIT_PERCENT}% | Stop Loss: {STOP_LOSS_PERCENT}%")
            # Verifica se precisamos fechar baseado em alvos de lucro/perda
            n.pnl_close(SYMBOL, TAKE_PROFIT_PERCENT, STOP_LOSS_PERCENT, account)
            
            # Após pnl_close pode ter fechado a posição, verifica novamente se ainda estamos em posição
            positions, im_in_pos, mypos_size, pos_sym, entry_px, pnl_perc, is_long = n.get_position(SYMBOL, account)
            
            if im_in_pos:
                print(f"{Fore.GREEN}✅ Posição atual mantida: {SYMBOL} {'LONG' if is_long else 'SHORT'} {mypos_size} @ ${entry_px} (PnL: {pnl_perc}%)")
                return  # Sai cedo já que estamos em uma posição
        else:
            print(f"{Fore.YELLOW}📉 Não em posição, procurando oportunidades de entrada...")
            # Cancela ordens pendentes antes de analisar novas entradas
            n.cancel_all_orders(account)
            print(f"{Fore.YELLOW}🚫 Cancelou todas as ordens existentes")
        
        # Busca e analisa dados de mercado
        df = fetch_klines(SYMBOL, interval='6h', limit=100)
        if df is None:
            return
            
        # Calcula indicadores
        df = calculate_indicators(df)
        if df is None:
            return
        
        # Verifica sinais de entrada
        long_signal, short_signal = check_for_entry_signals(df)
        
        # Se temos um sinal e não estamos em posição, entra em um trade
        if (long_signal or short_signal) and not im_in_pos:
            # Obtém dados do livro de ofertas
            print(f"\n{Fore.CYAN}📚 Buscando dados do livro de ofertas...")
            ask, bid, l2_data = n.ask_bid(SYMBOL)
            print(f"{Fore.GREEN}💰 Preço atual - Ask: ${ask:.2f}, Bid: ${bid:.2f}")
            
            # Ajusta alavancagem e tamanho da posição
            lev, pos_size = n.adjust_leverage_usd_size(SYMBOL, POSITION_SIZE_USD, LEVERAGE, account)
            print(f"{Fore.YELLOW}📊 Alavancagem: {lev}x | Tamanho da posição: {pos_size}")
            
            if long_signal:
                print(f"{Fore.GREEN}📈 Colocando ordem LIMIT BUY em ${bid}...")
                n.limit_order(SYMBOL, True, pos_size, bid, False, account)
                print(f"{Fore.GREEN}🎯 Razão da entrada: Rompimento do Squeeze BB com confirmação ADX")
                
            elif short_signal:
                print(f"{Fore.RED}📉 Colocando ordem LIMIT SELL em ${ask}...")
                n.limit_order(SYMBOL, False, pos_size, ask, False, account)
                print(f"{Fore.RED}🎯 Razão da entrada: Quebra do Squeeze BB com confirmação ADX")
                
            print(f"{Fore.YELLOW}⏳ Ordem colocada, aguardando execução...")
        else:
            if im_in_pos:
                print(f"{Fore.YELLOW}⏳ Já em posição, nenhuma nova ordem colocada")
            elif long_signal or short_signal:
                print(f"{Fore.YELLOW}⏳ Sinal detectado mas posição existe, pulando entrada")
            else:
                print(f"{Fore.YELLOW}⏳ Nenhum sinal de entrada detectado, continuando a monitorar...")
        
        # Easter egg
        print(f"\n{Fore.MAGENTA}🌕 XAUNOMAD diz: Paciência é fundamental com estratégias de squeeze! 🤖")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Erro na execução do bot: {str(e)}")
        print(f"{Fore.RED}📋 Rastreamento de pilha:\n{traceback.format_exc()}")

def main():
    """Ponto de entrada principal para o bot"""
    # Exibe banner
    print_banner()
    
    # Análise inicial de mercado
    print(f"{Fore.YELLOW}🔍 XAUNOMAD realizando análise inicial de mercado...")
    analyze_market()
    
    # Execução inicial do bot
    print(f"{Fore.YELLOW}🚀 Iniciando primeiro ciclo do bot XAUNOMAD...")
    bot()
    
    # Agenda o bot para executar a cada minuto
    schedule.every(1).minutes.do(bot)
    
    # Agenda análise de mercado para executar a cada hora
    schedule.every(1).hours.do(analyze_market)
    
    print(f"{Fore.GREEN}✅ Bot agendado para executar a cada minuto")
    print(f"{Fore.GREEN}✅ Análise de mercado agendada para executar a cada hora")
    
    while True:
        try:
            # Executa tarefas agendadas pendentes
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            print(f"{Fore.YELLOW}⚠️ Bot parado pelo usuário")
            break
        except Exception as e:
            print(f"{Fore.RED}❌ Encontrou um erro: {e}")
            print(f"{Fore.RED}📋 Rastreamento de pilha:\n{traceback.format_exc()}")
            # Espera antes de tentar novamente para evitar log rápido de erros
            time.sleep(10)

if __name__ == "__main__":
    main()
