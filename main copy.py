import traceback
from ib_insync import IB, Stock, Option, OptionChain
from ib_insync import *
import pandas as pd
import yfinance as yf
from volatile_tickers import volatile_tickers

from datetime import datetime, timedelta

def fetch_put_options_with_low_delta(ticker_symbol):
    """
    Fetches put options with delta < 0.15 for a given stock ticker.

    Args:
        ticker_symbol (str): The stock ticker symbol to fetch options for.
    """
    ib = IB()
    try:
        ib.connect('127.0.0.1', 7497, clientId=1)

        market_price = yf.Ticker(ticker_symbol).history(period='1d')['Close'].iloc[-1]

        stock = Stock(ticker_symbol, 'SMART', 'USD')

        ib.qualifyContracts(stock)

        chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
        if not chains:
            print(f"No options chains available for {ticker_symbol}.")
            return
        
        chain = next(c for c in chains if c.tradingClass == ticker_symbol and c.exchange == 'CBOE')

        today = datetime.now()
        min_date = int((today + timedelta(days=25)).strftime('%Y%m%d'))
        max_date = int((today + timedelta(days=47)).strftime('%Y%m%d'))
        expirations = [int(exp) for exp in chain.expirations if min_date <= int(exp) <= max_date]

        strikes = [strike for strike in chain.strikes
            if market_price * 0.95 < strike <= market_price * 0.98]

        # print(util.df(chains))
        # return

        # from itertools import islice
        # contracts = list(islice(
        #     (Option(stock.symbol, expiration, strike, 'P', 'SMART')
        #     for expiration in expirations
        #     for strike in strikes),
        #     100
        # ))

        contracts = [Option(stock.symbol, expiration, strike, 'P', 'SMART')
            for expiration in expirations
            for strike in strikes]

        contracts = ib.qualifyContracts(*contracts)
        print(len(contracts))

        # Live streaming (the default)
        # Frozen (typically used for bid/ask prices after market close)
        # Delayed (if the username does not have live market data subscriptions)
        # Delayed-Frozen (combination of types 2 & 3)

        filtered_options = []
        ib.reqMarketDataType(4)
        for contract in contracts:
            market_data = ib.reqMktData(contract, '', snapshot=True)
            ib.sleep(10)
            print(market_data)

            # Check delta and other fields
            if market_data.modelGreeks:
                delta = market_data.modelGreeks.delta
                bid_price = market_data.bid
                print(f"DELTA {delta}")
                print(f"BID {bid_price}")
                if delta and abs(delta) < 0.5 and bid_price*100 > 100 :
                    filtered_options.append({
                        'ticker': ticker_symbol,
                        'expiration': contract.lastTradeDateOrContractMonth,
                        'strike': contract.strike,
                        'delta': delta,
                        'impliedVolatility': market_data.modelGreeks.impliedVol,
                        'lastPrice': market_data.last,
                        'bid': market_data.bid,
                        'ask': market_data.ask,
                    })
            break

        ib.disconnect()

        if filtered_options:
            df = pd.DataFrame(filtered_options)
            print(df)
            today_date = datetime.now().strftime('%Y-%m-%d')  # Format the date as YYYY-MM-DD
            file_name = f"data/{today_date}.xlsx"  # Add the .xlsx extension
            df.to_excel(file_name, index=False)  # Save DataFrame to Excel without the index
            print(f"Data saved to {file_name}")
        else:
            print(f"No put options with delta < 0.15 found for {ticker_symbol}.")

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())  # Print the full traceback
        ib.disconnect()

if __name__ == "__main__":
    for ticker in volatile_tickers:
        fetch_put_options_with_low_delta(ticker)
