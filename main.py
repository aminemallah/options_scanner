# TO DO
# exit below earnings
# keep spreads tight

import traceback
from ib_insync import IB, Stock, Option
import pandas as pd
import yfinance as yf
from volatile_tickers import volatile_tickers
from datetime import datetime, timedelta
import logging

DELTA = 0.25
CAPITAL = 60000
EXPIRY_START = 5
EXPIRY_END = 40
RETURN_PER_DAY = 0.06
RETURN_TOTAL_DAYS = 30

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='w'
)

class OptionFetcher:
    def __init__(self):
        self.ib = IB()
        self.data = []

    def connect(self):
        try:
            self.ib.connect('127.0.0.1', 7497, clientId=1)
        except Exception as e:
            print("Failed to connect to IB Gateway:", e)

    def disconnect(self):
        self.ib.disconnect()

    def fetch_put_options_with_low_delta(self, ticker_symbol):
        try:
            stock_yf = yf.Ticker(ticker_symbol)
            market_price = stock_yf.history(period='1d')['Close'].iloc[-1]
  
            stock = Stock(ticker_symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)

            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
            if not chains:
                print(f"No options chains available for {ticker_symbol}.")
                return

            chain = next((c for c in chains if c.tradingClass == ticker_symbol and c.exchange == 'CBOE'), None)
            if not chain:
                print(f"No suitable chain found for {ticker_symbol}.")
                return

            today = datetime.now()
            min_date = int((today + timedelta(days=EXPIRY_START)).strftime('%Y%m%d'))
            max_date = int((today + timedelta(days=EXPIRY_END)).strftime('%Y%m%d'))
            expirations = [int(exp) for exp in chain.expirations if min_date <= int(exp) <= max_date]

            strikes = [strike for strike in chain.strikes if market_price * 0.96 < strike <= market_price * 0.99]

            contracts = [Option(stock.symbol, expiration, strike, 'P', 'SMART')
                         for expiration in expirations for strike in strikes]

            contracts = self.ib.qualifyContracts(*contracts)
            logging.info(f"Qualified {len(contracts)} contracts for {ticker_symbol}")
            print(f"Qualified {len(contracts)} contracts for {ticker_symbol}")

            self.ib.reqMarketDataType(4)  # Delayed market data
            for contract in contracts:
                market_data = self.ib.reqMktData(contract, '', snapshot=True)
                self.ib.sleep(10)
                logging.info(market_data)
                if market_data.modelGreeks:
                    delta = market_data.modelGreeks.delta
                    bid_price = market_data.bid
                    ask_price = market_data.ask
                    strike_price = contract.strike
                    percentage_return = (bid_price/strike_price)* 100

                    expiration_date = datetime.strptime(contract.lastTradeDateOrContractMonth, '%Y%m%d')
                    days_till_expiration = (expiration_date - datetime.today()).days
                    required_total_return = RETURN_PER_DAY * days_till_expiration

                    if delta and abs(delta) < DELTA and percentage_return >= required_total_return:
                        logging.info("CONTRACT PASSED")
                        obj = {
                            'ticker': ticker_symbol,
                            'expiration': contract.lastTradeDateOrContractMonth,
                            'strike': contract.strike,
                            'delta': delta,
                            'impliedVolatility': market_data.modelGreeks.impliedVol,
                            'lastPrice': market_data.last,
                            'bid': market_data.bid,
                            'ask': market_data.ask,
                            f"percentageReturnPer{RETURN_TOTAL_DAYS}Days": (percentage_return/days_till_expiration)*RETURN_TOTAL_DAYS,
                            "premiumPerDay": (bid_price*100)/days_till_expiration,
                            "premiumTotal": bid_price*100
                        }
                        logging.info(obj)
                        print(obj)
                        self.data.append(obj)
        except Exception as e:
            print(f"Error processing {ticker_symbol}:")
            print(traceback.format_exc())

    def save_to_excel(self):
        if self.data:
            df = pd.DataFrame(self.data)
            today_date = datetime.now().strftime('%Y-%m-%d')  # Format the date as YYYY-MM-DD
            file_name = f"data/{today_date}.xlsx"  # Add the .xlsx extension
            df.to_excel(file_name, index=False)  # Save DataFrame to Excel without the index
            print(f"Data saved to {file_name}")
        else:
            print("No data to save.")

    def process_tickers(self, tickers):
        self.connect()
        for ticker in tickers:
            print(f"Processing ticker: {ticker}")
            self.fetch_put_options_with_low_delta(ticker)
        self.disconnect()
        self.save_to_excel()


if __name__ == "__main__":
    option_fetcher = OptionFetcher()
    option_fetcher.process_tickers(volatile_tickers)
