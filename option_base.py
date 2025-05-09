import traceback
from ib_async import IB, Stock, Option
# from ib_insync import IB, Stock, Option
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

RETURN_TOTAL_DAYS = 30

# csp
DELTA_CSP = 0.3
EXPIRY_START_CSP = 24
EXPIRY_END_CSP = 41
PERCENTAGE_RETURN_NOTIFY_CSP = 5.5
STRIKE_RATIO_START = 0.95
STRIKE_RATIO_END = 0.85

# cc
DELTA_CC = 0.3
EXPIRY_START_CC = 24
EXPIRY_END_CC = 81
PERCENTAGE_RETURN_NOTIFY_CC = 1.9

# c
DELTA_C = 0.9
EXPIRY_START_C = 200
EXPIRY_END_C = 300
RETURN_MULTIPLE = 10

vars = {
    'csp': {
        'DELTA': DELTA_CSP,
        'PERCENTAGE_RETURN_NOTIFY': PERCENTAGE_RETURN_NOTIFY_CSP,
        'EXPIRY_START': EXPIRY_START_CSP,
        'EXPIRY_END': EXPIRY_END_CSP
    },
    'cc': {
        'DELTA': DELTA_CC,
        'PERCENTAGE_RETURN_NOTIFY': PERCENTAGE_RETURN_NOTIFY_CC,
        'EXPIRY_START': EXPIRY_START_CC,
        'EXPIRY_END': EXPIRY_END_CC
    },
    'c': {
        'DELTA': DELTA_C,
        'RETURN_MULTIPLE': RETURN_MULTIPLE,
        'EXPIRY_START': EXPIRY_START_C,
        'EXPIRY_END': EXPIRY_END_C
    }
}

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='w'
)

class OptionBase:
    def __init__(self):
        self.ib = IB()
        self.ib.errorEvent += self.on_error
        self.data = []
        self.logger = logging

    def on_error(self, reqId, errorCode, errorString, contract=None):
        if errorCode == 10197:
            self.logger.error(f"Custom Handler: Market data unavailable due to competing live session (reqId={reqId})")
            self.error_10197_occurred = True

    def custom_reqMktData(self, contract):
        max_retries = 1
        retry_delay = 60
        retry_count = 0
        while True:
            self.error_10197_occurred = False
            self.logger.info(f"ATTEMPTING TO REQUEST MARKET DATA (attempt {retry_count + 1})")

            market_data = self.ib.reqMktData(contract, '', snapshot=True)
            self.logger.info("WAITING 15 SECONDS FOR MARKET DATA")
            self.ib.sleep(15)
            self.logger.info("MARKET DATA REQUEST DONE")

            if self.error_10197_occurred:
                self.logger.warning("⚠️ Market data error 10197 occurred: competing live session.")
                retry_count += 1
                if retry_count >= max_retries:
                    self.logger.error("Max retries reached. Aborting market data request.")
                    return market_data
                self.logger.info(f"Retrying in {retry_delay} seconds...")
                self.ib.sleep(retry_delay)
            else:
                self.logger.info("✅ Market data request successful.")
                return market_data

    def connect(self):
        try:
            self.ib.connect('127.0.0.1', 7497, clientId=1)
        except Exception as e:
            self.logger.error(f"Failed to connect to IB Gateway: {e}")

    def disconnect(self):
        self.ib.disconnect()

    def get_stock_price(self, ticker_symbol):
        stock_yf = yf.Ticker(ticker_symbol.replace(".", "-"))
        market_price = stock_yf.history(period='1d')['Close'].iloc[-1]
        return market_price

    def fetch_options_data(self, ticker_symbol, stock_price, option_type, strike_value_start, strike_value_end):
        try:
            stock = Stock(ticker_symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)

            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
            if not chains:
                self.logger.info(f"No options chains available for {ticker_symbol}.")
                return []

            chain = next((c for c in chains if c.tradingClass == ticker_symbol and c.exchange == 'CBOE'), None)
            if not chain:
                self.logger.info(f"No suitable chain found for {ticker_symbol}.")
                return []

            today = datetime.now()
            min_date = int((today + timedelta(days=vars[self.action_type]['EXPIRY_START'])).strftime('%Y%m%d'))
            max_date = int((today + timedelta(days=vars[self.action_type]['EXPIRY_END'])).strftime('%Y%m%d'))
            expirations = [int(exp) for exp in chain.expirations if min_date <= int(exp) <= max_date]

            # 🔄 Build strikes list from fixed values with 0.5 increments
            strikes = []
            current_strike = strike_value_start
            while current_strike <= strike_value_end:
                if current_strike in chain.strikes:
                    strikes.append(current_strike)
                current_strike = round(current_strike + 0.5, 2)

            contracts = [Option(stock.symbol, expiration, strike, option_type, 'SMART')
                         for expiration in expirations for strike in strikes]
            contracts = self.ib.qualifyContracts(*contracts)

            self.logger.info(f"Qualified {len(contracts)} contracts for {ticker_symbol}")
            self.logger.info(contracts)
            return contracts
        except Exception as e:
            self.logger.error(f"Error processing {ticker_symbol}: {traceback.format_exc()}")
            return []


    def save_to_excel(self):
        if self.data:
            df = pd.DataFrame(self.data)
            today_date = datetime.now().strftime('%Y-%m-%d')
            file_name = f"data/{today_date}-{self.action_type}.xlsx"
            df.to_excel(file_name, index=False)
            self.logger.info(f"Data saved to {file_name}")
        else:
            self.logger.info("No data to save.")

    def post_processing(self):
        import sys
        sys.path.append('../common')
        import common_utils
        keys_to_keep = [
            'ticker',
            'stockPrice',
            'expiration',
            'strike',
            'premium',
            'DTE',
            '100StockValue',
            'delta',
            f'percentageReturnPer{RETURN_TOTAL_DAYS}Days',
            'ticker',
            'longStrike',
            'shortStrike',
            'spread',
            'askLong',
            'bidShort',
            'netDebit',
            'returnMultiple'
        ]
        for data_obj in self.data:
            if (
                (f"percentageReturnPer{RETURN_TOTAL_DAYS}Days" in data_obj and
                (data_obj[f"percentageReturnPer{RETURN_TOTAL_DAYS}Days"] > vars[self.action_type]['PERCENTAGE_RETURN_NOTIFY']))
                or 
                ("returnMultiple" in data_obj and
                (data_obj["returnMultiple"] >= vars[self.action_type]['RETURN_MULTIPLE']))
                ):
                filtered_data = {key: data_obj[key] for key in keys_to_keep if key in data_obj}
                filtered_data['action'] = self.action_type
                message = "\n".join([f"{key}: {value}" for key, value in filtered_data.items()])
                common_utils.notify_message_aleph(f"{message}")

    def process_tickers(self, tickers, action_type):
        self.action_type = action_type
        self.connect()
        for ticker in tickers:
            try:
                self.logger.info(f"Processing ticker: {ticker['symbol']}")
                stock_price = self.get_stock_price(ticker['symbol'])
                self.fetch_put_options_with_low_delta(ticker['symbol'], stock_price, ticker['earnings_date'], ticker['strike_value_start'], ticker['strike_value_end'])
            except Exception as e:
                self.logger.error(e)
                traceback.print_exc()
        self.disconnect()
        self.save_to_excel()
        self.post_processing()
