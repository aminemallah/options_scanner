import traceback
from ib_insync import IB, Stock, Option
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='w'
)

class OptionBase:
    def __init__(self):
        self.ib = IB()
        self.data = []
        self.logger = logging

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

    def fetch_options_data(self, ticker_symbol, stock_price, expiry_start, expiry_end):
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
            min_date = int((today + timedelta(days=expiry_start)).strftime('%Y%m%d'))
            max_date = int((today + timedelta(days=expiry_end)).strftime('%Y%m%d'))
            expirations = [int(exp) for exp in chain.expirations if min_date <= int(exp) <= max_date]

            strikes = [strike for strike in chain.strikes if stock_price * 0.85 < strike <= stock_price]

            contracts = [Option(stock.symbol, expiration, strike, 'P', 'SMART')
                         for expiration in expirations for strike in strikes]
            contracts = self.ib.qualifyContracts(*contracts)

            self.logger.info(f"Qualified {len(contracts)} contracts for {ticker_symbol}")
            return contracts
        except Exception as e:
            self.logger.error(f"Error processing {ticker_symbol}: {traceback.format_exc()}")
            return []

    def save_to_excel(self):
        if self.data:
            df = pd.DataFrame(self.data)
            today_date = datetime.now().strftime('%Y-%m-%d')  # Format the date as YYYY-MM-DD
            file_name = f"data/{today_date}.xlsx"  # Add the .xlsx extension
            df.to_excel(file_name, index=False)  # Save DataFrame to Excel without the index
            self.logger.info(f"Data saved to {file_name}")
        else:
            self.logger.info("No data to save.")

    def process_tickers(self, tickers):
        self.connect()
        for ticker in tickers:
            try:
                self.logger.info(f"Processing ticker: {ticker['symbol']}")
                stock_price = self.get_stock_price(ticker['symbol'])
                self.fetch_put_options_with_low_delta(ticker['symbol'], stock_price, ticker['earnings_date'])
            except Exception as e:
                self.logger.error(e)
                traceback.print_exc()
        self.disconnect()
        self.save_to_excel()
        self.post_processing()
