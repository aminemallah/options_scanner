# TO DO
# exit below earnings
# keep spreads tight

from option_base import OptionBase
from volatile_tickers import volatile_tickers
from datetime import datetime
from logger_config import logger

DELTA = 0.25
EXPIRY_START = 2
EXPIRY_END = 20
RETURN_PER_DAY = 0.06
RETURN_TOTAL_DAYS = 30

class LowDeltaOptionFetcher(OptionBase):
    def fetch_put_options_with_low_delta(self, ticker_symbol):
        contracts = self.fetch_options_data(
            ticker_symbol,
            EXPIRY_START,
            EXPIRY_END
        )

        self.ib.reqMarketDataType(4)
        for contract in contracts:
            market_data = self.ib.reqMktData(contract, '', snapshot=True)
            self.ib.sleep(10)

            if market_data.modelGreeks:
                delta = market_data.modelGreeks.delta
                bid_price = market_data.bid
                percentage_return = (bid_price / contract.strike) * 100

                expiration_date = datetime.strptime(contract.lastTradeDateOrContractMonth, '%Y%m%d')
                days_till_expiration = (expiration_date - datetime.today()).days
                required_total_return = RETURN_PER_DAY * days_till_expiration

                if delta and abs(delta) < DELTA and percentage_return >= required_total_return:
                    logger.info("CONTRACT PASSES")
                    obj = {
                        'ticker': ticker_symbol,
                        'expiration': contract.lastTradeDateOrContractMonth,
                        'strike': contract.strike,
                        'delta': delta,
                        'impliedVolatility': market_data.modelGreeks.impliedVol,
                        'lastPrice': market_data.last,
                        'bid': market_data.bid,
                        f"percentageReturnPer{RETURN_TOTAL_DAYS}Days": (percentage_return / days_till_expiration) * RETURN_TOTAL_DAYS
                    }
                    self.data.append(obj)


if __name__ == "__main__":
    fetcher = LowDeltaOptionFetcher()
    fetcher.process_tickers(volatile_tickers)
