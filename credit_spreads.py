# TO DO
# for a spread of $%, i have to collect premium at least $1
#  delta < .25
# exit below earnings

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

TARGET_DELTA = 0.3
TARGET_PROFIT = 50

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

        strikes = [strike for strike in chain.strikes if market_price * 0.95 < strike <= market_price * 0.99]

        contracts = [Option(stock.symbol, expiration, strike, 'P', 'SMART')
                        for expiration in expirations for strike in strikes]

        contracts = self.ib.qualifyContracts(*contracts)
        logging.info(f"Qualified {len(contracts)} contracts for {ticker_symbol}")
        print(f"Qualified {len(contracts)} contracts for {ticker_symbol}")

        contracts_with_marketdata = []
        self.ib.reqMarketDataType(4)
        for contract in contracts:
            market_data = self.ib.reqMktData(contract, '', snapshot=True)
            self.ib.sleep(5)
            logging.info(market_data)
            if market_data.modelGreeks:
                contracts_with_marketdata.append({
                    "contract_obj": contract,
                    "marketdata": market_data
                })
    
        for current_index in range(len(contracts_with_marketdata) - 1, -1, -1):
            current_contract = contracts_with_marketdata[current_index]
            current_contract_bid = current_contract["marketdata"].bid
            current_contract_delta = current_contract["marketdata"].modelGreeks.delta
            current_contract_exp = current_contract["contract_obj"].lastTradeDateOrContractMonth

            if current_contract_delta and abs(current_contract_delta) < TARGET_DELTA:
                for preceding_index in range(current_index - 1, -1, -1):
                    preceding_contract = contracts_with_marketdata[preceding_index]
                    preceding_contract_ask = preceding_contract["marketdata"].ask
                    preceding_contract_exp = preceding_contract["contract_obj"].lastTradeDateOrContractMonth

                    if (current_contract_exp == preceding_contract_exp
                        and (current_contract_bid - preceding_contract_ask)*100 >= TARGET_PROFIT):

                        obj = {
                            'ticker': ticker_symbol,
                            'expiration': current_contract_exp,
                            'bid_strike': current_contract["contract_obj"].strike,
                            'ask_strike': preceding_contract["contract_obj"].strike,
                            'delta': current_contract["marketdata"].modelGreeks.delta,
                            'impliedVolatility': current_contract["marketdata"].modelGreeks.impliedVol,
                            'lastPrice': current_contract["marketdata"].last,
                            'bid': current_contract["marketdata"].bid,
                            'ask': current_contract["marketdata"].ask,
                        }

                        logging.info("CONTRACT PASSES::")
                        logging.info(obj)
                        self.data.append(obj)
     

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
