#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    *******************************************************************************************
    3CommasBot: 3Commas SmartTrades Bot
    Author: Ali Toori
    Website: https://boteaz.com/
    *******************************************************************************************
"""
import concurrent.futures
import json
import logging.config
import subprocess
import os
import requests
from pathlib import Path
from time import sleep
from datetime import datetime
import pandas as pd
import pyfiglet
from py3cw.request import Py3CW


class ThreeCommasBot:
    def __init__(self):
        self.PROJECT_ROOT = Path(os.path.abspath(os.path.dirname(__file__)))
        self.COM_HOME_URL = 'https://3Commas.io'
        self.file_cc = str(self.PROJECT_ROOT / '__pycache__/cc.py')
        self.file_settings = str(self.PROJECT_ROOT / '3CommasRes/Settings.json')
        self.file_pairs = str(self.PROJECT_ROOT / '3CommasRes/Pairs.csv')
        self.file_trades_stats = str(self.PROJECT_ROOT / '3CommasRes/SmartTradesStats.csv')
        self.file_trades_state = str(self.PROJECT_ROOT / '3CommasRes/SmartTradesStates.csv')
        self.settings = self.get_settings()["Settings"]
        self.api_name = self.settings['APIName']
        self.api_key = self.settings['APIKey']
        self.api_secret = self.settings['APISecret']
        self.client = None
        self.cc_status = False
        self.positions = {}
        self.position = False
        self.LOGGER = self.get_logger()
        # self.email_server = self.get_email_server()

    @staticmethod
    def get_logger():
        """
        Get logger file handler
        :return: LOGGER
        """
        logging.config.dictConfig({
            "version": 1,
            "disable_existing_loggers": False,
            'formatters': {
                'colored': {
                    '()': 'colorlog.ColoredFormatter',  # colored output
                    # --> %(log_color)s is very important, that's what colors the line
                    'format': '[%(asctime)s,%(lineno)s] %(log_color)s[%(message)s]',
                    'log_colors': {
                        'DEBUG': 'green',
                        'INFO': 'cyan',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'bold_red',
                    },
                },
                'simple': {
                    'format': '[%(asctime)s,%(lineno)s] [%(message)s]',
                },
            },
            "handlers": {
                "console": {
                    "class": "colorlog.StreamHandler",
                    "level": "INFO",
                    "formatter": "colored",
                    "stream": "ext://sys.stdout"
                },
                "file": {
                    "class": "logging.handlers.RotatingFileHandler",
                    "level": "INFO",
                    "formatter": "simple",
                    "filename": "3CommasBot.log",
                    "maxBytes": 1 * 1024 * 1024,
                    "backupCount": 1
                },
            },
            "root": {"level": "INFO",
                     "handlers": ["console", "file"]
                     }
        })
        return logging.getLogger()

    def get_email_server(self):
        """
        :return: email server
        """
        port = 465  # For SSL
        smtp_server = "smtp.gmail.com"
        sender_email = 'email@gmail.com'
        password = 'password123'
        context = ssl.create_default_context()
        email_server = smtplib.SMTP_SSL(smtp_server, port, context=context)
        email_server.login(sender_email, password)
        return email_server

    def send_telegram_msg(self, msg):
        bot_token = self.settings['BotToken']
        chat_id = self.settings['ChatID']
        send_text = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={chat_id}&text={msg}'
        response = requests.get(str(send_text))
        return response.json()

    @staticmethod
    def enable_cmd_colors():
        from sys import platform
        if platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(11), 7)

    # Get CC response
    def get_cc(self):
        # LOGGER.info(f'Getting CC: {self.FILE_CC_URL}')
        try:
            response = requests.get(url=self.FILE_CC_URL)
            return response.json()
        except:
            return None

    @staticmethod
    def banner():
        pyfiglet.print_figlet(text='____________ 3CommasBot\n', colors='RED')
        print('Author: Ali Toori, Full-Stack Python Developer\n'
              'Website: https://boteaz.com/\n'
              '************************************************************************')

    # Get settings from Setting.json file
    def get_settings(self):
        """
        Creates default or loads existing settings file.
        :return: settings
        """
        if os.path.isfile(self.file_settings):
            with open(self.file_settings, 'r') as f:
                settings = json.load(f)
            return settings
        settings = {"Settings": {
            "APIName": "Please set your API Name",
            "APIKey": "Please set your API Key",
            "APISecret": "Please set your API Secret"}}
        with open(self.file_settings, 'w') as f:
            json.dump(settings, f, indent=4)
        with open(self.file_settings, 'r') as f:
            settings = json.load(f)
        return settings

    # 3Commas authenticated Py3CW instance
    def get_3commas_api(self, api_key, secret):
        """
        :param api_key: API key for 3commas account
        :param secret: API secret for 3commas account
        :return: Authenticated object of Py3CW
        """
        return Py3CW(key=api_key, secret=secret,
                     request_options={
                         'request_timeout': 30,
                         'nr_of_retries': 5,
                         'retry_status_codes': [502]
                     })

    # Get accounts
    def get_accounts(self):
        """
        :param self.client: Py3CW object
        :return: accounts
        """
        error, accounts = self.client.request(entity='accounts', action='')
        self.LOGGER.info(f'Total accounts: {len(accounts)}')
        # accounts = json.loads(accounts)
        # accounts = json.dumps(accounts, indent=4, sort_keys=True)
        # self.LOGGER.info(f'Accounts Data: {accounts}')
        return accounts

    # Get bots
    def get_bot_data(self, bot_id):
        """
        :param bot_id: Bot ID
        :return: bots
        """
        self.LOGGER.info(f'Getting bot data: {bot_id}')
        error, bots = self.client.request(entity='bots', action='show', action_id=bot_id)
        self.LOGGER.info(f'Bot data count: {len(bots)}')
        # bots = json.loads(bots)
        bots = json.dumps(bots, indent=4, sort_keys=True)
        self.LOGGER.info(f'Bot Data: {bots}')
        return bots

    # Get deals
    def get_deals(self):
        """
        :return: deals
        """
        error, deals = self.client.request(entity='deals', action='')
        self.LOGGER.info(f'Deals count: {len(deals)}')
        # deals = json.loads(deals)
        deals = json.dumps(deals, indent=4, sort_keys=True)
        self.LOGGER.info(f'Deals Data: {deals}')
        return deals

    # Get account stats
    def get_account_balance(self, account_id):
        """
        :param self.client: Py3CW object
        :param account_id: account id to get balance of
        :return: type: float, account_balance
        """
        error, data = self.client.request(entity='accounts', action='load_balances', action_id=str(account_id))
        if data:
            balance = data["usd_amount"]
            return round(float(balance), 2)
        else:
            if error and "msg" in error:
                self.LOGGER.info(f'Error while fetching account balance: {error["msg"]}')
        return None

    # Get deals stats
    def get_deals_stats(self, bot_id):
        """
        :param self.client: Py3CW object
        :param bot_id: bot id to get stats of
        :return: deals stats of the bot
        """
        error, deals_stats = self.client.request(entity='bots', action='deals_stats', action_id=bot_id,
                                                 payload={"bot_id": bot_id})
        self.LOGGER.info(f'Total deals stats: {len(deals_stats)}')
        # deals = json.loads(deals)
        deals_stats = json.dumps(deals_stats, indent=4, sort_keys=True)
        self.LOGGER.info(f'Deals Stats: {deals_stats}')
        return deals_stats

    # Update 3Commas bot's deal with new SL and TP
    def update_deal(self, bot_data, deal, new_stoploss, new_take_profit):
        """Update bot with new SL and TP."""
        bot_name = bot_data["name"]
        deal_id = deal["id"]
        error, data = self.client.request(entity="deals", action="update_deal", action_id=str(deal_id),
                                          payload={
                                              "deal_id": bot_data["id"],
                                              "stop_loss_percentage": new_stoploss,
                                              "take_profit": new_take_profit})
        if data:
            self.LOGGER.info(f"Changing SL for deal {deal_id}/{deal['pair']} on bot \"{bot_name}\"\n"
                             f"Changed SL from {deal['stop_loss_percentage']}% to {new_stoploss}%. "
                             f"Changed TP from {deal['take_profit']}% to {new_take_profit}")
        else:
            if error and "msg" in error:
                self.LOGGER.error("Error occurred updating bot with new SL/TP values: %s" % error["msg"])
            else:
                self.LOGGER.error("Error occurred updating bot with new SL/TP values")

    def get_pair_price(self, pair="USDT_ADA"):
        """Get current pair value to calculate amount to buy"""
        self.LOGGER.info(f'Fetching 3Commas {pair} price')
        error, data = self.client.request(
            entity="accounts",
            action="currency_rates",
            payload={"market_code": "binance", "pair": pair},
        )
        if data:
            price = float(data["last"])
            self.LOGGER.info(f'Current price of {pair} is: {price}')
            return price
        else:
            if error and "msg" in error:
                self.LOGGER.info(f'Fetching 3Commas {pair} price failed with error: {error["msg"]}')
            else:
                self.LOGGER.info(f"Fetching 3Commas {pair} price failed")
        return None

    def get_smart_trade(self, account_id, pair, pair_price, pair_qty, order_type, level=1):
        position_type = "buy"
        tp1 = round(pair_price + (self.settings['TakeProfit1'] / 100 * pair_price), 5)
        tp2 = round(pair_price + (self.settings['TakeProfit2'] / 100 * pair_price), 5)
        sl = round(pair_price - (self.settings['TrailingStopLoss'] / 100 * pair_price), 5)
        if account_id == self.settings['AccountIDShort']:
            position_type = "sell"
            tp1 = round(pair_price - (self.settings['TakeProfit1'] / 100 * pair_price), 5)
            tp2 = round(pair_price - (self.settings['TakeProfit2'] / 100 * pair_price), 5)
            sl = round(pair_price + (self.settings['TrailingStopLoss'] / 100 * pair_price), 5)
        smart_trade = {
            "account_id": account_id,
            "instant": "false",
            "pair": pair,
            "note": f"Level: {level}",
            "leverage": {
                "enabled": "true",
                "type": "isolated",
                "value": self.settings['Leverage']},
            "position": {
                "type": position_type,
                "units": {
                    "value": pair_qty},
                "order_type": order_type
            },
            "take_profit": {
                "enabled": "true",
                "steps": [
                    {
                        "order_type": order_type,
                        "price": {
                            "type": "bid",
                            "value": tp1},
                        "volume": 50.0},
                    {
                        "order_type": order_type,
                        "price": {
                            "type": "bid",
                            "value": tp2},
                        "volume": 50.0}
                ]},
            "stop_loss": {
                "enabled": "true",
                "order_type": order_type,
                "conditional": {
                    "price": {
                        "type": "bid",
                        "value": sl},
                    "trailing": {
                        "enabled": "true",
                        "percent": -self.settings['TrailingStopLoss']}
                }
            }
        }
        return smart_trade

    def place_smart_trade(self, smart_trade):
        error, data = self.client.request(
            entity='smart_trades_v2',
            action='new',
            payload=smart_trade
        )
        if data:
            self.LOGGER.info(f'SmartTrade has been placed: {json.dumps(data, indent=4)}')
            return data
        else:
            if error and "msg" in error:
                self.LOGGER.info(f'SmartTrade error: {error}')
            else:
                self.LOGGER.info(f"SmartTrade error")
        return None

    def get_smart_trade_by_id(self, smart_trade_id):
        # Get SmartTrade history
        self.LOGGER.info(f'Fetching SmartTrade {smart_trade_id} history')
        error, data = self.client.request(
            entity='smart_trades_v2',
            action='get_by_id',
            action_id=str(smart_trade_id),
        )
        if data:
            return data
        else:
            if error and "msg" in error:
                self.LOGGER.info(f'Fetching SmartTrade {smart_trade_id} failed with error: {error}')
            else:
                self.LOGGER.info(f"Fetching SmartTrade {smart_trade_id} failed")
        return None

    # Main Strategy
    def strategy(self, pair):
        level = 1
        tp_count = 0
        tsl_count = 0
        trade_count = 2
        pnl = 0
        pnls = [0] * 8
        start_time = datetime.now().strftime("%H:%M:%S")
        order_type = self.settings['OrderType']
        amount_usdt = self.settings['AmountUSDT']
        check_interval = self.settings['CheckInterval']
        if os.path.isfile(self.file_trades_state):
            trades_state = pd.read_csv(self.file_trades_state, index_col=None)
            time_stamp = trades_state.iloc[0]['TimeStamp']
            start_time = trades_state.iloc[0]['StartTime']
            pair = trades_state.iloc[0]['Pair']
            smart_trade_id_l = str(trades_state.iloc[0]['SmartTradeLong'])
            smart_trade_id_s = str(trades_state.iloc[0]['SmartTradeShort'])
            pnl = float(trades_state.iloc[0]['PnL'])
            level = int(trades_state.iloc[0]['Level'])
            trade_count = int(trades_state.iloc[0]['TradeCount'])
            tp_count = int(trades_state.iloc[0]['TPCount'])
            tsl_count = int(trades_state.iloc[0]['TSLCount'])
            pnls[level] = pnl
        else:
            pair_price = self.get_pair_price(pair=pair)
            pair_qty = round(amount_usdt / pair_price, 3)
            self.LOGGER.info(f'Pair: {pair}, Quantity to trade: {pair_qty} {pair}')
            self.LOGGER.info(f'Pair: {pair}, Placing SmartTrades with {amount_usdt}USD, sides: LONG & SHORT')
            smart_trade_l = self.get_smart_trade(account_id=self.settings['AccountIDLong'], pair=pair, pair_price=pair_price, pair_qty=pair_qty, order_type=order_type, level=level)
            smart_trade_s = self.get_smart_trade(account_id=self.settings['AccountIDShort'], pair=pair, pair_price=pair_price, pair_qty=pair_qty, order_type=order_type, level=level)

        while True:
            self.LOGGER.info(f'Pair: {pair}, Checking SmartTrades status in {check_interval} seconds')
            sleep(check_interval)
            smart_trade_history_l = self.get_smart_trade_by_id(smart_trade_id=smart_trade_id_l)
            smart_trade_history_s = self.get_smart_trade_by_id(smart_trade_id=smart_trade_id_s)
            if smart_trade_history_l is None or smart_trade_history_s is None:
                continue
            smart_trade_status_l = str(smart_trade_history_l["status"]["title"])
            smart_trade_tp_l = float(smart_trade_history_l["profit"]["usd"])
            smart_trade_status_s = str(smart_trade_history_s["status"]["title"])
            smart_trade_tp_s = float(smart_trade_history_s["profit"]["usd"])
            pnls[level] = smart_trade_tp_l + smart_trade_tp_s
            pnl = sum(pnls)
            self.LOGGER.info(f'Pair: {pair} | SmartTrade status: Long: {smart_trade_status_l} Short: {smart_trade_status_s} | TP Long: {smart_trade_tp_l} TP Short: {smart_trade_tp_s} | PnL: {pnl} | Trade count: {trade_count} | Level: {level} | TP count: {tp_count} TSL count: {tsl_count}')
            if 'failed' in smart_trade_status_l.lower() or 'failed' in smart_trade_status_s.lower():
                self.send_telegram_msg(msg=f'TimeStamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, Pair: {pair}, SmartTrade Status: Failed')
            # If hits TP, place order same as the previous position
            if tp_count == 1:
                self.LOGGER.info(f'Pair: {pair} | SmartTrades hit TP: {smart_trade_history_l["profit"]["usd"]} | {smart_trade_history_s["profit"]["usd"]} | PnL: {pnl} | Placing SmartTrades with {amount_usdt}USDT')
                self.LOGGER.info(f'Pair: {pair} | SmartTrade status: Long: {smart_trade_status_l} Short: {smart_trade_status_s} | TP Long: {smart_trade_tp_l} TP Short: {smart_trade_tp_s} | PnL: {pnl} | Trade count: {trade_count} | Level: {level} | TP count: {tp_count} TSL count: {tsl_count}')
                trade_state = {"TimeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "StartTime": start_time,
                               "Pair": pair, "SmartTradeLong": smart_trade_id_l, "SmartTradeShort": smart_trade_id_s,
                               "PnL": pnl, "Level": level, "TradeCount": trade_count, "TPCount": tp_count,
                               "TSLCount": tsl_count}
                state_df = pd.DataFrame([trade_state])
                state_df.to_csv(self.file_trades_state, index=False)
                self.LOGGER.info(f'SmartTradesState updated: {state_df.head()}')
                trade_stats = {"TimeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pair": pair, "Trade count": trade_count, "Level": level, "TP count": tp_count, "TSL count": tsl_count}
                self.send_telegram_msg(msg=json.dumps(trade_stats, indent=4))
                stats_df = pd.DataFrame([trade_stats])
                if not os.path.isfile(self.file_trades_stats):
                    stats_df.to_csv(self.file_trades_stats, index=False)
                else:  # else if exists so append without writing the header
                    stats_df.to_csv(self.file_trades_stats, mode='a', header=False, index=False)
                level = 1
                pnls = [0] * 8
                pnl = 0
                pair_price = self.get_pair_price(pair=pair)
                amount_usdt = self.settings['AmountUSDT']
                pair_qty = round(amount_usdt / pair_price, 3)

                smart_trade_id_l = smart_trade_response_l["id"]
                smart_trade_id_s = smart_trade_response_s["id"]
                trade_count += 2
            # If hits TSL, place order with 2x the previous position
            elif "" == "":
                # If level reaches 7, start over from the base order
                self.LOGGER.info(f'Pair: {pair} | SmartTrade status: Long: {smart_trade_status_l} Short: {smart_trade_status_s} | TP Long: {smart_trade_tp_l} TP Short: {smart_trade_tp_s} | PnL: {pnl} | Trade count: {trade_count} | Level: {level} | TP count: {tp_count} TSL count: {tsl_count}')
                if level == 7:
                    tsl_count += 1
                    pair_price = self.get_pair_price(pair=pair)
                    amount_usdt = self.settings['AmountUSDT']
                    pair_qty = round(amount_usdt / pair_price, 3)
                    self.LOGGER.info(f'Pair: {pair}, Level reached 7, starting again from base order')
                    self.LOGGER.info(f'Pair: {pair}, SmartTrades hit TSL: {float(smart_trade_history_l["profit"]["usd"])} {float(smart_trade_history_s["profit"]["usd"])} | PnL: {pnl} | Placing SmartTrades with {amount_usdt}USDT')

                    smart_trade_id_l = smart_trade_response_l["id"]
                    smart_trade_id_s = smart_trade_response_s["id"]
                    trade_count += 2
                    trade_state = {"TimeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "StartTime": start_time,
                                   "Pair": pair, "SmartTradeLong": smart_trade_id_l,
                                   "SmartTradeShort": smart_trade_id_s, "PnL": pnl, "Level": level,
                                   "TradeCount": trade_count, "TPCount": tp_count, "TSLCount": tsl_count}
                    state_df = pd.DataFrame([trade_state])
                    state_df.to_csv(self.file_trades_state, index=False)
                    self.LOGGER.info(f'SmartTradesState updated: {state_df.head()}')
                    trade_stats = {"TimeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pair": pair, "Trade count": trade_count, "Level": level, "TP count": tp_count, "TSL count": tsl_count}
                    self.send_telegram_msg(msg=json.dumps(trade_stats, indent=4))
                    stats_df = pd.DataFrame([trade_stats])
                    if not os.path.isfile(self.file_trades_stats):
                        stats_df.to_csv(self.file_trades_stats, index=False)
                    else:  # else if exists so append without writing the header
                        stats_df.to_csv(self.file_trades_stats, mode='a', header=False, index=False)
                    level = 1
                    pnls = [0] * 8
                    pnl = 0
                else:
                    pair_price = self.get_pair_price(pair=pair)
                    amount_usdt = round(amount_usdt * 2, 2)
                    pair_qty = round(amount_usdt / pair_price, 3)
                    level += 1
                    self.LOGGER.info(f'Pair: {pair}, SmartTrades hit TSL: {float(smart_trade_history_l["profit"]["usd"])} {float(smart_trade_history_s["profit"]["usd"])} | PnL: {pnl} | Placing SmartTrades with {amount_usdt}USDT')
                    trade_count += 2
                    trade_state = {"TimeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "StartTime": start_time,
                                   "Pair": pair, "SmartTradeLong": smart_trade_id_l,
                                   "SmartTradeShort": smart_trade_id_s, "PnL": pnl, "Level": level,
                                   "TradeCount": trade_count, "TPCount": tp_count, "TSLCount": tsl_count}
                    state_df = pd.DataFrame([trade_state])
                    state_df.to_csv(self.file_trades_state, index=False)
                    self.LOGGER.info(f'SmartTradesState updated: {state_df.head()}')
                    trade_stats = {"TimeStamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "Pair": pair, "Trade count": trade_count, "Level": level, "TP count": tp_count, "TSL count": tsl_count}
                    stats_df = pd.DataFrame([trade_stats])
                    if not os.path.isfile(self.file_trades_stats):
                        stats_df.to_csv(self.file_trades_stats, index=False)
                    else:  # else if exists so append without writing the header
                        stats_df.to_csv(self.file_trades_stats, mode='a', header=False, index=False)
            # If time laps 24Hrs, send Telegram alert

            time_laps = datetime.now().strftime("%H:%M:%S")
            if start_time == time_laps:
                self.send_telegram_msg(msg=f'TimeStamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, Pair: {pair} Bot Status: Working ...')

    def main(self):
        self.enable_cmd_colors()
        self.banner()
        self.LOGGER.info(f'3CommasBot launched')
        self.client = self.get_3commas_api(api_key=self.api_key, secret=self.api_secret)
        pairs_list = pd.read_csv(self.file_pairs, index_col=None)
        pairs_list = [pair['Pair'] for pair in pairs_list.iloc]
        self.LOGGER.info(f'Trading pairs: {pairs_list}')
        account_balance_long = self.get_account_balance(account_id=self.settings['AccountIDLong'])
        account_balance_short = self.get_account_balance(account_id=self.settings['AccountIDShort'])
        self.LOGGER.info(f'Account balance LONG: {account_balance_long}')
        self.LOGGER.info(f'Account balance SHORT: {account_balance_short}')
        self.strategy(pair=pairs_list[0])
        # with concurrent.futures.ThreadPoolExecutor(max_workers=len(pairs_list)) as executor:
        #     results = executor.map(self.strategy, pairs_list)
        #     try:
        #         for x, result in results:
        #             self.LOGGER.info(f'Results: {result}')
        #     except Exception as e:
        #         self.LOGGER.info(e)


if __name__ == '__main__':
    ThreeCommasBot().main()
