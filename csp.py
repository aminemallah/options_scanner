# TO DO
# exit below earnings
# keep spreads tight

import traceback
from option_base import OptionBase
# from volatile_tickers import volatile_tickers
from datetime import datetime

DELTA = 0.8
EXPIRY_START = 2
EXPIRY_END = 15
RETURN_PER_DAY = 0.06
RETURN_TOTAL_DAYS = 30

class LowDeltaOptionFetcher(OptionBase):
    def fetch_put_options_with_low_delta(self, ticker_symbol, stock_price):
        contracts = self.fetch_options_data(
            ticker_symbol,
            stock_price,
            EXPIRY_START,
            EXPIRY_END
        )

        self.ib.reqMarketDataType(4)
        for contract in contracts:
            market_data = self.ib.reqMktData(contract, '', snapshot=True)
            self.ib.sleep(10)
            self.logger.info(market_data)
            self.ib.cancelMktData(contract)
            self.ib.sleep(2)

            if market_data.modelGreeks:
                delta = market_data.modelGreeks.delta
                bid_price = market_data.bid
                percentage_return = (bid_price / contract.strike) * 100

                expiration_date = datetime.strptime(contract.lastTradeDateOrContractMonth, '%Y%m%d')
                days_till_expiration = (expiration_date - datetime.today()).days
                required_total_return = RETURN_PER_DAY * days_till_expiration


                normalized_delta = 1 - (abs(delta) / DELTA)
                normalized_percentage_return = (percentage_return - RETURN_PER_DAY) / (
                    required_total_return - RETURN_PER_DAY
                )
                normalized_percentage_return = max(0, min(normalized_percentage_return, 1))
                score = 0.5 * normalized_delta + 0.5 * normalized_percentage_return

                if delta and abs(delta) < DELTA and percentage_return >= required_total_return:
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
                        f"percentageReturnPer{RETURN_TOTAL_DAYS}Days": (percentage_return / days_till_expiration) * RETURN_TOTAL_DAYS,
                        'score': score
                    }
                    self.data.append(obj)


if __name__ == "__main__":

    from fetch_stocks import MarketChameleonScraper
    stocks_fetcher = MarketChameleonScraper()
    volatile_tickers = stocks_fetcher.load_page()

    fetcher = LowDeltaOptionFetcher()
    fetcher.process_tickers(volatile_tickers)
