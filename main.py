import traceback
from ib_insync import IB, Stock, Option
import pandas as pd
import yfinance as yf
from volatile_tickers import volatile_tickers
from datetime import datetime, timedelta
import logging

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
        """
        Fetches put options with delta < 0.15 for a given stock ticker.

        Args:
            ticker_symbol (str): The stock ticker symbol to fetch options for.
        """
        try:
            market_price = yf.Ticker(ticker_symbol).history(period='1d')['Close'].iloc[-1]
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
            min_date = int((today + timedelta(days=25)).strftime('%Y%m%d'))
            max_date = int((today + timedelta(days=47)).strftime('%Y%m%d'))
            expirations = [int(exp) for exp in chain.expirations if min_date <= int(exp) <= max_date]

            strikes = [strike for strike in chain.strikes if market_price * 0.95 < strike <= market_price * 0.98]

            contracts = [Option(stock.symbol, expiration, strike, 'P', 'SMART')
                         for expiration in expirations for strike in strikes]

            contracts = self.ib.qualifyContracts(*contracts)
            logging.info(f"Qualified {len(contracts)} contracts for {ticker_symbol}")
            print(f"Qualified {len(contracts)} contracts for {ticker_symbol}")

            self.ib.reqMarketDataType(4)  # Delayed market data
            for contract in contracts:
                market_data = self.ib.reqMktData(contract, '', snapshot=True)
                self.ib.sleep(5)
                logging.info(market_data)
                if market_data.modelGreeks:
                    delta = market_data.modelGreeks.delta
                    bid_price = market_data.bid
                    if delta and abs(delta) < 0.5 and bid_price * 100 > 100:
                        obj = {
                            'ticker': ticker_symbol,
                            'expiration': contract.lastTradeDateOrContractMonth,
                            'strike': contract.strike,
                            'delta': delta,
                            'impliedVolatility': market_data.modelGreeks.impliedVol,
                            'lastPrice': market_data.last,
                            'bid': market_data.bid,
                            'ask': market_data.ask,
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
