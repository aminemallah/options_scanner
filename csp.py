# TO DO
# keep spreads tight

from option_base import OptionBase
from datetime import datetime
from datetime import datetime, timedelta
import json

DELTA = 0.3
EXPIRY_START = 2
EXPIRY_END = 35
RETURN_TOTAL_DAYS = 30

class LowDeltaOptionFetcher(OptionBase):
    def fetch_put_options_with_low_delta(self, ticker_symbol, stock_price, earnings_date):
        contracts = self.fetch_options_data(
            ticker_symbol,
            stock_price,
            EXPIRY_START,
            EXPIRY_END
        )

        if earnings_date:
            earnings_date_dt = datetime.strptime(earnings_date, '%Y%m%d')
            if earnings_date_dt <= datetime.today():
                earnings_date_dt = datetime.today() + timedelta(days=365 * 10)
            min_expiration_date = earnings_date_dt - timedelta(days=7)
        else:
            min_expiration_date = datetime(2100, 1, 1)

        self.ib.reqMarketDataType(4)
        for contract in contracts:
            expiration_date = datetime.strptime(contract.lastTradeDateOrContractMonth, '%Y%m%d')
            days_till_expiration = (expiration_date - datetime.today()).days + 1
            if expiration_date >= min_expiration_date:
                self.logger.info("CONTRACT FAILS: Expiration date is too close to earnings date.")
                continue

            market_data = self.ib.reqMktData(contract, '', snapshot=True)
            self.ib.sleep(10)
            self.logger.info(market_data)
            self.ib.cancelMktData(contract)
            self.ib.sleep(2)

            if market_data.modelGreeks:
                delta = market_data.modelGreeks.delta
                bid_price = market_data.bid
                if delta and abs(delta) < DELTA:
                    self.logger.info("CONTRACT PASSES")
                    obj = {
                        'ticker': ticker_symbol,
                        "stockPrice": stock_price,
                        'expiration': contract.lastTradeDateOrContractMonth,
                        'strike': contract.strike,
                        'premium': bid_price*100,
                        'premiumPerDay': (bid_price*100)/days_till_expiration,
                        'DTE': days_till_expiration,
                        'AmountNeededToBuyStock': contract.strike*100,
                        'delta': delta,
                        'impliedVolatility': market_data.modelGreeks.impliedVol,
                        'bid': market_data.bid,
                        f"percentageReturnPer{RETURN_TOTAL_DAYS}Days":  (((bid_price/days_till_expiration)*RETURN_TOTAL_DAYS) / contract.strike) * 100
                    }
                    self.data.append(obj)

    def post_processing(self):
        import sys
        sys.path.append('../common')
        import common_utils

        for data_obj in self.data:
            if (abs(data_obj['delta']) < 0.2
                and data_obj[f"percentageReturnPer{RETURN_TOTAL_DAYS}Days"] > 2):
                message = "\n".join([f"{key}: {value}" for key, value in data_obj.items()])
                common_utils.notify_message_aleph(
                    f"{message}"
                )


if __name__ == "__main__":
    # from volatile_tickers import volatile_tickers
    from fetch_stocks import MarketChameleonScraper
    stocks_fetcher = MarketChameleonScraper()
    volatile_tickers = json.loads(stocks_fetcher.load_page())

    from mag7 import stocks
    volatile_tickers_new = []
    for volatile_ticker in volatile_tickers:
        if volatile_ticker['symbol'] in stocks:
            volatile_tickers_new.append(volatile_ticker)

    fetcher = LowDeltaOptionFetcher()
    fetcher.process_tickers(volatile_tickers_new)
