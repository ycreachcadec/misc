"""
get last messages from given discord channel
"""
from binance.client import Client
import requests
import json
import time
from datetime import datetime, timezone
from dateutil import parser


CURRENT_PRICE = PREVIOUS_PRICE = INITIAL_PRICE = TRADE_START_TIME = None
LOOP_EVOLUTIONS = []
OVERALL_EVOLUTIONS = []
FEES_RATE = 0.00075
FEES_PAYED = 0.0
USDT_BALANCE = INITIAL_USDT_BALANCE = 100.0
USDT_BALANCE_HISTORY = []
COIN_BALANCE = 0

def get_clean_float(unclean_float, digits=4):
    return float(f"%.{digits}f" % unclean_float)

def get_percentage(number1, number2):
    return get_clean_float( ((number2/number1) -1 ) *100)

def buy():
    global USDT_BALANCE
    global FEES_PAYED
    global COIN_BALANCE

    fees = get_clean_float(USDT_BALANCE * FEES_RATE)


    FEES_PAYED = get_clean_float( FEES_PAYED + fees )
    usdt_buy_amount = get_clean_float( USDT_BALANCE - fees )
    COIN_BALANCE = get_clean_float( usdt_buy_amount / CURRENT_PRICE)
    print(f"[BUY] Completed - Convert {USDT_BALANCE} USDT for {COIN_BALANCE} coins - Fees {fees}$")
    USDT_BALANCE = 0

def sell():
    global USDT_BALANCE
    global FEES_PAYED
    global COIN_BALANCE
    usdt_received_from_sell = get_clean_float( COIN_BALANCE * CURRENT_PRICE )
    fees = get_clean_float( usdt_received_from_sell * FEES_RATE )
    FEES_PAYED = get_clean_float( FEES_PAYED + fees )
    USDT_BALANCE = get_clean_float ( usdt_received_from_sell - fees )
    print(f"[SELL] Completed - Convert {COIN_BALANCE} coins for {USDT_BALANCE} USDT - Coin price {CURRENT_PRICE}$ -  Fees {fees}$")
    COIN_BALANCE = 0

def sell_simulation():
    usdt_received = get_clean_float( COIN_BALANCE * CURRENT_PRICE )
    fees = get_clean_float( usdt_received * FEES_RATE )
    usdt_received = usdt_received - fees
    print(f"[SELL-SIM] Completed - Convert {COIN_BALANCE} coins for {usdt_received} USDT - Coin price {CURRENT_PRICE}$ -  Fees {fees}$")
    return usdt_received

def trade_termination():
    global CURRENT_PRICE, PREVIOUS_PRICE, INITIAL_PRICE, TRADE_START_TIME, LOOP_EVOLUTIONS, OVERALL_EVOLUTIONS
    sell()
    final_percent_perf = get_percentage(INITIAL_USDT_BALANCE, USDT_BALANCE)
    print(f"[TERMINATION] Final performance on coin : {OVERALL_EVOLUTIONS[-1]}%")
    print(f"[TERMINATION] Final performance in USDT : {final_percent_perf}%")
    print(f"[TERMINATION] USDT balance : {USDT_BALANCE}$")
    CURRENT_PRICE = PREVIOUS_PRICE = INITIAL_PRICE = TRADE_START_TIME = None
    LOOP_EVOLUTIONS = OVERALL_EVOLUTIONS = []
    return final_percent_perf

def trade():
    global PREVIOUS_PRICE, LOOP_EVOLUTIONS, OVERALL_EVOLUTIONS
    
    print(f"New price : {CURRENT_PRICE}")
    print(f"Old price : {PREVIOUS_PRICE}")
    time_elapsed = (datetime.now() - TRADE_START_TIME).total_seconds()

    current_evolution =  get_percentage(PREVIOUS_PRICE, CURRENT_PRICE)
    overall_evolution =  get_percentage(INITIAL_PRICE, CURRENT_PRICE)
    LOOP_EVOLUTIONS.append(current_evolution)
    OVERALL_EVOLUTIONS.append(overall_evolution)

    streak_profit = 0
    for p in reversed(LOOP_EVOLUTIONS):
        if p < 0:
            break
        streak_profit = streak_profit + 1

    streak_loss = 0
    for p in reversed(LOOP_EVOLUTIONS):
        if p >= 0:
            break
        streak_loss = streak_loss + 1

    print(f"Streak positive evolutions of coin : {streak_profit}")
    print(f"Streak negative evolutions of coin : {streak_loss}")

    usdt_evolution = sell_simulation()
    usdt_evolution_percent = get_percentage(INITIAL_USDT_BALANCE, usdt_evolution)
    USDT_BALANCE_HISTORY.append(usdt_evolution_percent)

    print(f"[DM] Sell simulation USDT result on this loop : {usdt_evolution}$ - Performance {usdt_evolution_percent}%")

    #if current trade reduce overall benefit of -20% or more :
    if len(USDT_BALANCE_HISTORY) > 1 and usdt_evolution_percent > 0:
        previous_usdt_evolution_percent = USDT_BALANCE_HISTORY[-2]

        if previous_usdt_evolution_percent > 0:
            balance_percent = get_percentage(previous_usdt_evolution_percent, usdt_evolution_percent)

            # print(f"USDT evolution backlog : {USDT_BALANCE_HISTORY}")
            # print(f"previous USDT evolution in percent : {previous_usdt_evolution_percent}%")
            # print(f"current USDT evolution in percent : {usdt_evolution_percent}%")    
            # print(f"percent : {balance_percent}%")

            if usdt_evolution_percent > 1 and balance_percent <= -20:
                print(f"TP - Lost {balance_percent}% of overall potential profit on this loop")
                return trade_termination()

    if usdt_evolution_percent > 5 and streak_profit == 0:
        print(f"TP - USDT gain >= 5%")
        return trade_termination()

    if usdt_evolution_percent > 1 and current_evolution < -1.0:
        print(f"TP - Small loss with an overall positive USDT balance")
        return trade_termination()

    #deals with loss with a positive overall
    if usdt_evolution_percent > 1 and current_evolution < -1.0:
        print(f"TP - Small loss with an overall positive USDT balance")
        return trade_termination()

    #deals with consecutive loss with a positive overall
    if usdt_evolution_percent > 0.5 and streak_loss > 1:
        print(f"TP - {streak_loss} consecutives loss with an overall positive USDT balance")
        return trade_termination()

    deep = min(USDT_BALANCE_HISTORY)

    if deep < -3 and usdt_evolution_percent >= 0.2 and streak_profit == 0:
        print(f"TP - Recovery from a deep with an overall positive USDT balance")
        return trade_termination()

    if streak_loss > 2:
        print(f"TP - Exit trade, 3 consecutive loss loop")      
        return trade_termination()

    #deals with loss 
    if deep < -3 and overall_evolution < 0 and usdt_evolution_percent > deep/2 and streak_profit == 0:
        print(f"SL - Partial recovery from a deep")
        return trade_termination()

    # if len(USDT_BALANCE_HISTORY) < 3 and deep <= -2.5:
    #     print(f"SL - Bad result on the very begining of the trade")
    #     return trade_termination()

    if usdt_evolution_percent < -2 and time_elapsed >= 600:
        print(f"SL - Bad overall result  on a >=10min trade")
        return trade_termination()

    if usdt_evolution_percent < -3 and time_elapsed >= 1200:
        print(f"SL - Bad overall result on a >=20min trade")
        return trade_termination()

    if usdt_evolution_percent < -4 and time_elapsed >= 1800:
        print(f"SL - Bad overall result on a >=30min trade")
        return trade_termination()

    if usdt_evolution_percent <= -5 and streak_profit == 0:
        print(f"SL - USDT loss <= -6%")
        return trade_termination()

    if len(LOOP_EVOLUTIONS) > 9:
        last_10_operations_average = sum(LOOP_EVOLUTIONS[-10:])/10
        if last_10_operations_average <= 0 and usdt_evolution_percent > 0 and streak_profit == 0:
            print(f"average of 10 last results is negative ({sum(LOOP_EVOLUTIONS[-10:])/10}) but overall results is positive, SELL")
            return trade_termination()

    PREVIOUS_PRICE = CURRENT_PRICE
    print("######")
    return None
    

def gen_trade_from_history():
    PAIR = "MDTUSDT"
    global CURRENT_PRICE, INITIAL_PRICE, PREVIOUS_PRICE
    global TRADE_START_TIME


    #CURRENT_PRICE = client.get_ticker(symbol=PAIR)['lastPrice']

    api_key = ""
    api_secret = ""
    # client = Client(api_key, api_secret)
    # klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 11:04 am +0100")

    PAIR = "WINGUSDT"
    PAIR = "API3USDT"
    PAIR = "MDTUSDT"
    PAIR = "ONGUSDT"
    client = Client(api_key, api_secret)
    klines = client.get_historical_klines(PAIR, Client.KLINE_INTERVAL_1MINUTE, "13 Feb 2022 07:32 pm +0100")

    INITIAL_PRICE = CURRENT_PRICE = PREVIOUS_PRICE = float(klines[0][4])
    TRADE_START_TIME = datetime.now()
    buy()
    for kline in klines:
        CURRENT_PRICE = float(kline[4])
        if trade():
            break

def loop_on_discord_msg():
    global CURRENT_PRICE, INITIAL_PRICE, PREVIOUS_PRICE 
    global TRADE_START_TIME
    AUTHORIZATION = ""
    DISCORD_CHANNEL_ID = ""
    api_key = ""
    api_secret = ""
    client = Client(api_key, api_secret)
    headers = {
        "authorization" : AUTHORIZATION 
    }
    endpoint = f"https://discord.com/api/v9/channels/{DISCORD_CHANNEL_ID}/messages?limit=10"

    r = requests.get(endpoint, headers=headers)
    messages = json.loads(r.text)

    ids = []
    total_positive_trades = []
    total_negative_trades = []
    last_trade_pair = None
    last_trade_datetime = datetime.now()

    while True:
        r = requests.get(endpoint, headers=headers)
        messages = json.loads(r.text)
        for message in messages:
            message_datetime = parser.parse(message['timestamp'])
            current_id = message["id"]
            if current_id not in ids:
                ids.append(current_id)

                increase = None #in case it is not define in message
                print(f"DEBUG : {message}")
                for line in message['content'].split('\n'):
                    if line.startswith('🚀'):
                        pair = line.split(' ')[1]
                    if line.startswith('#️⃣'):
                        count = line.split(' : ')[1]
                    if line.startswith('📈'):
                        increase = line.split(': ')[1]
                    if line.startswith('🚥'):
                        risk = line.split(':')[1]
                print(f"New alert at {message['timestamp']} on {pair} - count {count} - increase since first alert : {increase} - Risk : {risk}")
                trade_pair = pair.replace('/', '')

                now = datetime.now()
                now_utc  = datetime.now(timezone.utc)
                message_datetime = parser.parse(message['timestamp'])
                message_age = (now_utc - message_datetime).total_seconds()
                last_trade_age = (now - last_trade_datetime).total_seconds()
                waiter_same_pair = 90

                if message_age < 60:
                    if trade_pair != last_trade_pair or last_trade_age >= waiter_same_pair:

                        ###
                        # INIT OF TRADE
                        ###
                        INITIAL_PRICE = CURRENT_PRICE = PREVIOUS_PRICE = float(client.get_ticker(symbol=trade_pair)['lastPrice'])
                        TRADE_START_TIME = datetime.now()
                        buy()

                        while True:
                            time.sleep(30)
                            CURRENT_PRICE = float(client.get_ticker(symbol=trade_pair)['lastPrice'])
                            trade_result = trade()
                            if trade_result:
                                break

                        if trade_result >= 0:
                            total_positive_trades.append(trade_result)
                        else:
                            total_negative_trades.append(trade_result)
                    else:
                        print(f"Last trade on pair {trade_pair} too recent ({last_trade_age}sec)")
                else:
                    print(f"Message too old : {message_age} seconds, skip")
                    print("#####")
        print(f"sleep 30sec - current : {USDT_BALANCE}$ - Total fees payed {FEES_PAYED}$ - Total positive trades : {total_positive_trades} - Total negative trades : {total_negative_trades}")
        time.sleep(30)



if __name__ == "__main__":
    # while True:
    #     trade_result = foo("AUTOUSDT")
    #     USDT_BALANCE = USDT_BALANCE + ( USDT_BALANCE * (trade_result/100) )
    #     print(f"Mise update : {USDT_BALANCE}")
    #     time.sleep(30)
    #print(get_messages())
    #foo("BETAUSDT")
    loop_on_discord_msg()
