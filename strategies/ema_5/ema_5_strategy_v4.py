
from colorama import Fore
import pandas as pd
import datetime
import time
import talib
import threading
from utilities import algo_util as utility
import logging

logger = logging.getLogger(__name__)

def process(name, status):
    risk_capacity = 300
    ema_period = 5
    timeframe = '5min'
    tgt_multiplier = 3
    traded = False
    trigger_candle_count = 0

    while getTradeTime() and status['traded'] != 'yes':
        try:
            dx = utility.get_historical_data(name="NSE:" + name + "-EQ", interval=timeframe, timeperiod=3)
            df = pd.DataFrame()
            df = df.append(dx)

            df['5ema'] = talib.EMA(df['close'], timeperiod=ema_period)

            trigger_candle = df.iloc[-3]
            signal_candle = df.iloc[-2]
            current_candle = df.iloc[-1]

            if trigger_candle_count == 0: candle_size = 1.007
            if trigger_candle_count == 1: candle_size = 1.006
            if trigger_candle_count == 2: candle_size = 1.005

            trigger_candle_formed = trigger_candle['close'] > (trigger_candle['low'] * candle_size)

            if trigger_candle_formed:
                trigger_candle_count = trigger_candle_count + 1

            signal_candle_formed = trigger_candle_formed and signal_candle['low'] > signal_candle['5ema']

            if signal_candle_formed:
                status['name'] = name
                status['state'] = 'Ready for sell'
                status['entry_price'] = signal_candle['low']
                status['sl_price'] = trigger_candle['high'] if trigger_candle['high'] > signal_candle['high'] else signal_candle['high']
            else:
                continue

            sell_signal_formed = current_candle['low'] < status['entry_price']

            if sell_signal_formed:
                logger.info(f"Signal for trade : {signal_candle_formed and sell_signal_formed and traded is False} for {name}")
                logger.info(f"{Fore.YELLOW} Signal for {name} on {datetime.datetime.now().time()} {Fore.WHITE} \n")

                status['sell_date'] = current_candle['date']
                status['entry_time'] = current_candle['date'].time()

                try:
                    qty = int(risk_capacity / (status['sl_price'] - status['entry_price']))
                except Exception as e:
                    logger.info(f"trade not taken for {name} as SL, entry values are not valid")
                    return

                status['qty'] = qty
                if qty <= 0:
                    logger.info(f"trade not taken for {name} as SL value exceeds risk capacity")
                else:
                    sl_points = round((status['sl_price'] - status['entry_price']) * 20.0) / 20.0
                    tg_points = round((tgt_multiplier * sl_points) * 20.0) / 20.0

                    data = {
                        "symbol": "NSE:" + name + "-EQ",
                        "qty": qty,
                        "type": 2,
                        "side": -1,
                        "productType": "BO",
                        "limitPrice": 0,
                        "stopPrice": 0,
                        "validity": "DAY",
                        "disclosedQty": 0,
                        "offlineOrder": "False",
                        "stopLoss": sl_points,
                        "takeProfit": tg_points
                    }
                    response = utility.place_order(data)
                    logger.info(f"Response : {response}")
                    if response is not None:
                        status['traded'] = 'yes'
                        logger.info(f"Trade : {status}")

        except Exception as e:
            logger.info(f"Error occurred : {e}")
        time.sleep(3)

def getTradeTime():
    return datetime.time(9, 15) < datetime.datetime.now().time() < datetime.time(10, 00)

def ema5Strategy(watchlist):

    for name in watchlist:
        status = getEmptyStatusObject()
        x = threading.Thread(target=process, args=(name,status,))
        logger.info(f"Thread started for {name}")
        x.start()
        time.sleep(3)

def getEmptyStatusObject():
    return {
        'state': None,
        'buysell': None,
        'name': None,
        'sell_date': None,
        'entry_time': None,
        'entry_price': None,
        'signal_candle_date': None,
        'traded': None,
        'qty': None,
        'sl_price': None,
        'tg': None,
        'exit_time': None,
        'exit_price': None,
        'pnl': None,
        'target_hit': None,
        'sl_hit': None,
    }
