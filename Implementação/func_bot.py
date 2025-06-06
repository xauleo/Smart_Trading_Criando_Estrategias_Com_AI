from eth_account.signers.local import LocalAccount
import eth_account
import json
import time 
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import ccxt
import pandas as pd
import datetime
import schedule 
import requests 
from datetime import datetime, timedelta
import pandas_ta as ta
import ccxt 
print('XAUNOMAD está ativo!')
from termcolor import colored


def ask_bid(symbol):
    """
    Obtém preços de ask e bid do livro de ordens
    """
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}

    data = {
        'type': 'l2Book',
        'coin': symbol
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    l2_data = response.json()
    l2_data = l2_data['levels']

    # obtém bid e ask 
    bid = float(l2_data[0][0]['px'])
    ask = float(l2_data[1][0]['px'])

    return ask, bid, l2_data


    
def get_sz_px_decimals(symbol):
    """
    Retorna com sucesso decimais de Tamanho e decimais de Preço

    Esta função retorna os decimais de tamanho para um determinado símbolo
    que é - o TAMANHO que você pode comprar ou vender
    ex. se decimal sz == 1 então você pode comprar/vender 1.4
    se decimal sz == 2 então você pode comprar/vender 1.45
    se decimal sz == 3 então você pode comprar/vender 1.456

    se o tamanho não estiver correto, recebemos este erro. para evitá-lo use a função sz decimal
    {'error': 'Invalid order size'}
    """
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    data = {'type': 'meta'}

    response = requests.post(url, headers=headers, data=json.dumps(data))

    if response.status_code == 200:
        # Sucesso
        data = response.json()
        #print(data)
        symbols = data['universe']
        symbol_info = next((s for s in symbols if s['name'] == symbol), None)
        if symbol_info:
            sz_decimals = symbol_info['szDecimals']
            
        else:
            print('Símbolo não encontrado')
    else:
        # Erro
        print('Erro:', response.status_code)

    ask = ask_bid(symbol)[0]
    # print(f'este é o ask {ask}')

    # Calcula o número de casas decimais no preço ask
    ask_str = str(ask)
    print(f'este é o ask str {ask_str}')
    if '.' in ask_str:
        px_decimals = len(ask_str.split('.')[1])
    else:
        px_decimals = 0

    print(f'{symbol} este é o preço: {ask}  decimal(is) sz {sz_decimals}, decimal(is) px {px_decimals}')

    return sz_decimals, px_decimals

def adjust_leverage_usd_size(symbol, usd_size, leverage, account):
    """
    Calcula o tamanho baseado em um valor específico em dólares USD
    """

    print('alavancagem:', leverage)

    #account: LocalAccount = eth_account.Account.from_key(key)
    exchange = Exchange(account, constants.MAINNET_API_URL)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Obtém o estado do usuário e imprime informações de alavancagem
    user_state = info.user_state(account.address)
    acct_value = user_state["marginSummary"]["accountValue"]
    acct_value = float(acct_value)

    print(exchange.update_leverage(leverage, symbol, is_cross=False))

    price = ask_bid(symbol)[0]

    # tamanho == saldo / preço * alavancagem
    # INJ 6.95 ... com alavancagem 10x... 10 INJ == $custo 6.95
    size = (usd_size / price) * leverage
    size = float(size)
    rounding = get_sz_px_decimals(symbol)[0]
    size = round(size, rounding)
    print(f'este é o tamanho de crypto que usaremos {size}')

    user_state = info.user_state(account.address)
        
    return leverage, size


def get_ohlcv2(symbol, interval, lookback_days):
    """
    Obtém dados OHLCV (Open, High, Low, Close, Volume) para análise
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=lookback_days)
    
    url = 'https://api.hyperliquid.xyz/info'
    headers = {'Content-Type': 'application/json'}
    data = {
        "type": "candleSnapshot",
        "req": {
            "coin": symbol,
            "interval": interval,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000)
        }
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        snapshot_data = response.json()
        return snapshot_data
    else:
        print(f"Erro ao buscar dados para {symbol}: {response.status_code}")
        return None
    

def get_position(symbol, account):
    """
    Obtém as informações da posição atual, como tamanho etc.
    """

    # account = LocalAccount = eth_account.Account.from_key(key)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    user_state = info.user_state(account.address)
    print(f'este é o valor atual da conta: {user_state["marginSummary"]["accountValue"]}')
    positions = []
    print(f'este é o símbolo {symbol}')
    print(user_state["assetPositions"])
    for position in user_state["assetPositions"]:
        if (position["position"]["coin"] == symbol) and float(position["position"]["szi"]) != 0:
            positions.append(position["position"])
            in_pos = True 
            size = float(position["position"]["szi"])
            pos_sym = position["position"]["coin"]
            entry_px = float(position["position"]["entryPx"])
            pnl_perc = float(position["position"]["returnOnEquity"])*100
            print(f'esta é a porcentagem de pnl {pnl_perc}')
            break 
    else:
        in_pos = False 
        size = 0 
        pos_sym = None 
        entry_px = 0 
        pnl_perc = 0

    if size > 0:
        long = True 
    elif size < 0:
        long = False 
    else:
        long = None 

    return positions, in_pos, size, pos_sym, entry_px, pnl_perc, long


def limit_order(coin, is_buy, sz, limit_px, reduce_only, account):
    """
    Coloca uma ordem limitada na exchange
    """
    exchange = Exchange(account, constants.MAINNET_API_URL)
    
    rounding = get_sz_px_decimals(coin)[0]
    sz = round(sz,rounding)
    print(f"🌙 XAUNOMAD colocando ordem:")
    print(f"Símbolo: {coin}")
    print(f"Lado: {'COMPRA' if is_buy else 'VENDA'}")
    print(f"Tamanho: {sz}")
    print(f"Preço: ${limit_px}")
    print(f"Reduzir Apenas: {reduce_only}")

    order_result = exchange.order(coin, is_buy, sz, limit_px, {"limit": {"tif": "Gtc"}}, reduce_only=reduce_only)
    print(f"🔍 Resultado bruto da ordem (tipo {type(order_result)}): {order_result}")

    if isinstance(order_result, dict) and 'response' in order_result:
        print(f"✅ Ordem colocada com status: {order_result['response']['data']['statuses'][0]}")
    else:
        print(f"✅ Ordem colocada (resposta bruta)")

    return order_result


def cancel_all_orders(account):
    """
    Cancela todas as ordens pendentes
    """
    exchange = Exchange(account, constants.MAINNET_API_URL)
    print("🚫 XAUNOMAD cancelando todas as ordens...")
    try:
        result = exchange.cancel_all_orders()
        print(f"✅ Todas as ordens canceladas: {result}")
        return result
    except Exception as e:
        print(f"❌ Erro ao cancelar ordens: {str(e)}")
        return None


def pnl_close(symbol, take_profit_percent, stop_loss_percent, account):
    """
    Fecha posição baseado em alvos de take profit e stop loss
    """
    positions, in_pos, size, pos_sym, entry_px, pnl_perc, is_long = get_position(symbol, account)
    
    if not in_pos:
        print("📈 XAUNOMAD: Não há posição para fechar")
        return False
    
    # Verifica condições de fechamento
    should_close = False
    reason = ""
    
    if pnl_perc >= take_profit_percent:
        should_close = True
        reason = f"Take Profit atingido ({pnl_perc:.2f}% >= {take_profit_percent}%)"
    elif pnl_perc <= stop_loss_percent:
        should_close = True
        reason = f"Stop Loss atingido ({pnl_perc:.2f}% <= {stop_loss_percent}%)"
    
    if should_close:
        print(f"💰 XAUNOMAD fechando posição: {reason}")
        try:
            # Fecha a posição fazendo ordem oposta
            ask, bid, _ = ask_bid(symbol)
            close_price = bid if is_long else ask
            close_size = abs(size)
            
            # Ordem de fechamento (oposta à posição atual)
            result = limit_order(symbol, not is_long, close_size, close_price, True, account)
            print(f"✅ XAUNOMAD: Posição fechada com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao fechar posição: {str(e)}")
            return False
    else:
        print(f"📊 XAUNOMAD: Posição mantida (PnL: {pnl_perc:.2f}%)")
        return False