from binance.client import Client
import requests
import json
import time
from datetime import datetime, timezone
from dateutil import parser
import random
from decimal import *

CAPITAL = INITIAL_CAPITAL = 100
EVOLUTIONS = []
COIN = 0.0
FEES_PAYED = 0
FEES_RATE = 0.001
BUY_POOL = [] #use to keep track of buy done
BUY_ORDERS = [] #buy orders in current grid 
SELL_ORDERS = [] #sell orders in current grid 
ACTIVE_ORDER = None #Keep track of latest trigger order 
INITIAL_PRICE = CURRENT_PRICE = None
TAKE_PROFIT = None

def get_percentage(number1, number2):
    return get_clean_float( ((number2/number1) -1 ) *100)

def get_clean_float(unclean_float, digits=8):
    return float(f"%.{digits}f" % unclean_float)

def buy_coins(coin_price, buy_amount):
    """
    buy coins
    """
    global CAPITAL
    global COIN
    global FEES_RATE
    global FEES_PAYED

    CAPITAL = get_clean_float(CAPITAL - buy_amount)
    fees = get_clean_float(buy_amount * FEES_RATE)
    FEES_PAYED = get_clean_float(FEES_PAYED + fees)
    buy_amount = get_clean_float(buy_amount - fees)
    coins_received = get_clean_float(buy_amount / coin_price)

    COIN = get_clean_float(COIN + coins_received)

    print(f"[buy] Buy price {coin_price}$ - amount {buy_amount}$ - Receive {coins_received} coins - Fees {fees}$")
    return coins_received


def sell_coins(coin_price, coins_amount_to_sell):
    """
    sell coins
    """
    global CAPITAL
    global COIN
    global FEES_RATE
    global FEES_PAYED

    COIN = get_clean_float(COIN - coins_amount_to_sell)
    if COIN < 0.00001:
        COIN = 0

    usdt_received = get_clean_float(coin_price * coins_amount_to_sell)
    fees = get_clean_float(usdt_received * FEES_RATE)
    FEES_PAYED = get_clean_float(FEES_PAYED + fees)
    usdt_received = get_clean_float(usdt_received - fees)
    CAPITAL = get_clean_float(CAPITAL + usdt_received)
    print(f"[sell] Sell price {coin_price}$ - amount {coins_amount_to_sell} coins - Receive {usdt_received}$ - Fees {fees}$")

def grid_init(grid_size):
    global BUY_POOL
    global ACTIVE_ORDER
    global BUY_ORDERS
    global SELL_ORDERS

    bottom_grid = get_clean_float(INITIAL_PRICE * 0.98, 4)
    top_grid = get_clean_float(INITIAL_PRICE * 1.02, 4)
    grid_range = top_grid - bottom_grid 
    grid_segment = get_clean_float(grid_range / grid_size , 4)

    print(f"[grid-init] Initial price : {INITIAL_PRICE}")
    print(f"[grid-init] Bottom grid : {bottom_grid}")
    print(f"[grid-init] Top grid : {top_grid}")
    print(f"[grid-init] Grid range : {grid_range}")
    print(f"[grid-init] Grid segment : {grid_segment}")

    ladder = [bottom_grid]

    while max(ladder) < top_grid:
        ladder.append( get_clean_float(ladder[-1] + grid_segment , 4 ) )

    print(f"[grid-init] ladder generated : {ladder}")
    ACTIVE_ORDER = min(ladder, key=lambda x:abs(x-CURRENT_PRICE))
    print(f"[grid-init] Nearest order to current price : {ACTIVE_ORDER}")
    BUY_ORDERS = [order for order in ladder if order < INITIAL_PRICE and order != ACTIVE_ORDER]
    SELL_ORDERS = [order for order in ladder if order > INITIAL_PRICE and order != ACTIVE_ORDER]
    print(f"[grid-init] Buy orders generated : {BUY_ORDERS}")
    print(f"[grid-init] Sell orders generated : {SELL_ORDERS}")
    print("----------")

def first_buy():
    """
    first buy
    """
    print(f"[first-buy] begin")
    usdt_buy_amount = get_clean_float( CAPITAL / ( len(BUY_ORDERS) + 1 ) ) #Buy the current 
    print(f"[first-buy] buy {100/(len(BUY_ORDERS) + 1)}% of capital as first buy")
    received_coins = buy_coins(CURRENT_PRICE, usdt_buy_amount )
    BUY_POOL.append(received_coins)
    print(f"[first-buy] end")
    print("----------")

def grid_loop():
    """
    grid loop
    """
    global BUY_POOL
    global SELL_ORDERS
    global BUY_ORDERS
    global ACTIVE_ORDER
    global EVOLUTIONS

    print(f"[grid-loop] start - loop price : {CURRENT_PRICE}$")
    print(f"[grid-loop] start - coins amount : {COIN}")
    print(f"[grid-loop] start - capital remaining : {CAPITAL}$")
    print(f"[grid-loop] start - buy orders : {BUY_ORDERS}")
    print(f"[grid-loop] start - sell orders : {SELL_ORDERS}")

    ### BUY PART
    triggered_buy_orders = [order for order in BUY_ORDERS if CURRENT_PRICE <= order]
    if triggered_buy_orders:
        triggered_buy_orders_length = len(triggered_buy_orders)
        print(f"[grid-loop] New price {CURRENT_PRICE}$ has triggered following buy orders : {triggered_buy_orders}")
        
        #Get current length of triggered buy_orders and make it a percentage of the total of buy orders
        #Buy coins with this percentage of remaining capital
        buy_percent_amount =  get_clean_float( triggered_buy_orders_length / len(BUY_ORDERS) )
        print(f"[grid-loop] Buy {buy_percent_amount*100}% of remaining capital at the current price")

        received_coins = buy_coins(CURRENT_PRICE, CAPITAL * buy_percent_amount )

        #In case multiple buy orders was triggered, adds the associated order number in the BUY_POOL
        buy_part = get_clean_float(received_coins / triggered_buy_orders_length)
        for i in range(triggered_buy_orders_length):
            BUY_POOL.append(buy_part)
            print(f"[grid-loop] BUY_POOL updated with following buy completed : {buy_part}")        

        #put previous active order as new sell order
        SELL_ORDERS.append(ACTIVE_ORDER)
        SELL_ORDERS.sort()
        print(f"[grid-loop] Added previous active order in SELL_ORDERS : {ACTIVE_ORDER}")

        #update new trigger order
        ACTIVE_ORDER = triggered_buy_orders[0] # Get lowest buy order triggered as new trigger order
        print(f"[grid-loop] new ACTIVE_ORDER : {ACTIVE_ORDER}")

        for order in triggered_buy_orders:
            BUY_ORDERS.remove(order)
        print(f"[grid-loop] Removed following orders from BUY_ORDERS : {triggered_buy_orders}")
        
        #remove new active order of triggered buy orders for injection in SELL_ORDERS
        triggered_buy_orders.remove(ACTIVE_ORDER)

        for order in triggered_buy_orders:
            SELL_ORDERS.append(order)
        SELL_ORDERS.sort()
        print(f"[grid-loop] Added following orders in SELL_ORDERS : {triggered_buy_orders}")

    ### SELL PART
    triggered_sell_orders = [order for order in SELL_ORDERS if CURRENT_PRICE > order]
    if triggered_sell_orders:
        print(f"[grid-loop] New price {CURRENT_PRICE}$ has triggered following sell orders : {triggered_sell_orders}")

        triggered_sell_orders_length = len(triggered_sell_orders)

        buy_orders_to_sell = BUY_POOL[-triggered_sell_orders_length:]

        print(f"[grid-loop] {triggered_sell_orders_length} sell orders were triggered, pulled {buy_orders_to_sell} from BUY_POOL")

        sell_amount = sum(buy_orders_to_sell)
        
        sell_coins(CURRENT_PRICE, sell_amount)
        print(f"[grid-loop] Sell {sell_amount} coins")
        
        for buy_order in buy_orders_to_sell:
            BUY_POOL.remove(buy_order)

        print(f"[grid-loop] following sell order(s) removed from BUY_POOL : {buy_orders_to_sell}")   

        #put previous active order as new buy order
        BUY_ORDERS.append(ACTIVE_ORDER)
        BUY_ORDERS.sort()
        print(f"[grid-loop] Added previous active order in BUY_ORDERS : {ACTIVE_ORDER}")

        #update new trigger order
        ACTIVE_ORDER = triggered_sell_orders[-1] # Get biggest sell order triggered as new trigger order
        print(f"[grid-loop] new ACTIVE_ORDER : {ACTIVE_ORDER}")

        for order in triggered_sell_orders:
            #remove triggered order from sell orders list
            SELL_ORDERS.remove(order)
        print(f"[grid-loop] Removed following orders from SELL_ORDERS : {triggered_sell_orders}")

        #remove new active order of triggered sell orders for injection in BUY_ORDERS
        triggered_sell_orders.remove(ACTIVE_ORDER)        
        for order in triggered_sell_orders:
            BUY_ORDERS.append(order)
        BUY_ORDERS.sort()            
        print(f"[grid-loop] Added following orders in BUY_ORDERS : {triggered_sell_orders}")

    #potential result
    p_usdt_amount = get_clean_float(COIN * CURRENT_PRICE)
    p_fees = get_clean_float(p_usdt_amount * FEES_RATE)
    p_usdt_amount = get_clean_float(p_usdt_amount - p_fees)
    p_usdt_overall = CAPITAL + p_usdt_amount
    p_usdt_performance = get_percentage(INITIAL_CAPITAL, p_usdt_overall)
    EVOLUTIONS.append(p_usdt_performance)

    print(f"[grid-loop] end - loop price : {CURRENT_PRICE}$")
    print(f"[grid-loop] end - coins amount : {COIN}")
    print(f"[grid-loop] end - capital remaining : {CAPITAL}$")
    print(f"[grid-loop] end - fees payed : {FEES_PAYED}$")
    print(f"[grid-loop] end - buy orders : {BUY_ORDERS}")
    print(f"[grid-loop] end - sell orders : {SELL_ORDERS}")
    print(f"[grid-loop] end - buy pool : {BUY_POOL}")
    print(f"[grid-loop] end - potential overall USDT : {p_usdt_overall}$")
    print(f"[grid-loop] end - Global potential USDT performance in % : {p_usdt_performance}%")
    print(f"[grid-loop] end - All evolutions in % : {EVOLUTIONS}")
    print(f"[grid-loop] end - Top evolution in % : {max(EVOLUTIONS)}")


    if COIN == 0 and p_usdt_performance >= TAKE_PROFIT:
        print(f"[grid-loop] end - Overall performance >= {TAKE_PROFIT}% without any coin remaining, end trade")
        return True

    if p_usdt_performance >= TAKE_PROFIT and COIN > 0:
        sell_coins(CURRENT_PRICE, COIN)
        print(f"[grid-loop] end - Overall performance >= {TAKE_PROFIT}% ( {p_usdt_performance}% ) with remaining coins {COIN}, sell and end trade")
        return True
    # print(f"new buy orders : {BUY_ORDERS}")
    # print(f"new sell orders : {SELL_ORDERS}")
    # print(f"current buy log state : {BUY_POOL}")
    # print(f"USDT amount : {CAPITAL}")
    # print(f"Coin amount : {round(COIN, 2)} ")
    # print(f"Fees payed : {FEES_PAYED}$")
    # print("#####")
    print("----------")

def main_bot():
    global INITIAL_PRICE, CURRENT_PRICE

    
    api_key = ""
    api_secret = ""
    client = Client(api_key, api_secret)

    klines = client.get_historical_klines("BONDUSDT", Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
    print(len(klines))

    for kline in klines[:-2]:
        print(kline)
    # PAIR = "BETAUSDT"
    # INITIAL_PRICE = CURRENT_PRICE = float(client.get_ticker(symbol=PAIR)['lastPrice'])

    # grid_init(12)
    # first_buy()

    # while True:
    #     time.sleep(30)
    #     CURRENT_PRICE = float(client.get_ticker(symbol=PAIR)['lastPrice'])
    #     grid_loop()

def main_manual():
    global INITIAL_PRICE, CURRENT_PRICE

    
    INITIAL_PRICE = CURRENT_PRICE = 1.5
    PAIR = "UMAUSDT"
    api_key = ""
    api_secret = ""

    client = Client(api_key, api_secret)
    klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 17:56 pm +0100")

    evolutions = []

    price = float(klines[0][4])

    for kline in klines:
        evol = round ( ( float(kline[4]) / price ) - 1.0 , 4 )
        evolutions.append(evol)
        price = float(kline[4])

    print(f"evolution generated from pair {PAIR} : {evolutions}")
    time.sleep(5)
    print("######")

    # RANDOM
    # evolutions = []
    # for _ in range(40):
    #     evolutions.append(round( random.uniform(-0.02, 0.02) ,4))

    # for _ in range(20):
    #     evolutions.append(round( random.uniform(-0.04, 0.04) ,4))

    # for _ in range(10):
    #     evolutions.append(round( random.uniform(-0.08, 0.08) ,4))

    # random.shuffle(evolutions)


    # print(f"evolutions generated : {evolutions}")
    grid_init(12)
    first_buy()

    for evolution in evolutions:
        time.sleep(0.2)
        CURRENT_PRICE = CURRENT_PRICE + ( CURRENT_PRICE * evolution )
        grid_loop()

    # RANDOM
    # print(f"evolutions generated : {evolutions}")
    # global_evol = 1
    # for evolution in evolutions:
    #     global_evol = global_evol + (global_evol * evolution)
    # print(f"global evol : {global_evol}")

def main_based_on_history():
    global INITIAL_PRICE, CURRENT_PRICE, TAKE_PROFIT
    
    api_key = ""
    api_secret = ""

    client = Client(api_key, api_secret)






    # PAIR = "BETAUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 03:55 am +0100")

    # PAIR = "MDTUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 10:33 am +0100")

    # PAIR = "OMUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 10:44 am +0100")

    # PAIR = "MDTUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 11:00 am +0100")

    # PAIR = "API3USDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 17:54 am +0100")

    # PAIR = "MLNUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 20:19 am +0100")

    # PAIR = "RAREUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 20:53 am +0100")

    # PAIR = "RAREUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 20:53 am +0100")

    # PAIR = "ONGUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 19:24 am +0100")


    # PAIR = "RADUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 21:14 am +0100")

    # PAIR = "DFUSDT"
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 21:09 am +0100")
    PAIR = "OGUSDT"
    klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 21:11 am +0100")

    PAIR = "RAREUSDT"
    klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 20:54 am +0100")


    TAKE_PROFIT = 1 # take profit in %
    INITIAL_PRICE = CURRENT_PRICE = float(klines[0][4])
    grid_init(20)
    first_buy()

    total_min = 0
    for kline in klines:
        total_min = total_min + 1
        time.sleep(0.05)
        CURRENT_PRICE = float(kline[4])
        trade_completed = grid_loop()
        if trade_completed:
            break
        if total_min > 1800:
            print("deal longer than 4H, break")
            break
    print(f"Deal ended in {total_min} minutes")
if __name__ == "__main__":
    # while True:
    #     trade_result = foo("AUTOUSDT")
    #     MISE = MISE + ( MISE * (trade_result/100) )
    #     print(f"Mise update : {MISE}")
    #     time.sleep(30)
    #print(get_messages())
    #foo("BETAUSDT")
    #main_manual()
    main_based_on_history()
