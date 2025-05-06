from option_base import OptionBase
from datetime import datetime, timedelta
import json

RETURN_TOTAL_DAYS = 30

class LowDeltaOptionFetcher(OptionBase):
    def fetch_put_options_with_low_delta(self, ticker_symbol, stock_price, earnings_date, strike_value_start, strike_value_end):
        contracts = self.fetch_options_data(
            ticker_symbol,
            stock_price,
            option_type='C',
            strike_value_start=strike_value_start,
            strike_value_end=strike_value_end
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
                gamma = market_data.modelGreeks.gamma
                vega = market_data.modelGreeks.vega
                theta = market_data.modelGreeks.theta
                implied_volatility = market_data.modelGreeks.impliedVol
                bid_price = market_data.bid

                if delta:
                    self.logger.info("CONTRACT PASSES")
                    obj = {
                        'ticker': ticker_symbol,
                        "stockPrice": stock_price,
                        'expiration': contract.lastTradeDateOrContractMonth,
                        'strike': contract.strike,
                        'premium': bid_price * 100,
                        'premiumPerDay': (bid_price * 100) / days_till_expiration,
                        'DTE': days_till_expiration,
                        '100StockValue': stock_price * 100,
                        'delta': delta,
                        'bid': bid_price,
                        f"percentageReturnPer{RETURN_TOTAL_DAYS}Days": (((bid_price / days_till_expiration) * RETURN_TOTAL_DAYS) / stock_price) * 100,
                        'impliedVolatility': implied_volatility,
                        'gamma': gamma,
                        'vega': vega,
                        'theta': theta,
                    }
                    self.data.append(obj)


if __name__ == "__main__":
    stocks = [
        {'symbol': "NVDA", 'earnings_date': "19700101", 'strike_value_start': 130, 'strike_value_end': 135},
        {'symbol': "HOOD", 'earnings_date': "19700101", 'strike_value_start': 75, 'strike_value_end': 85},
        {'symbol': "SOFI", 'earnings_date': "19700101", 'strike_value_start': 15, 'strike_value_end': 16},
        {'symbol': "RKLB", 'earnings_date': "19700101", 'strike_value_start': 39, 'strike_value_end': 41},
        # {'symbol': "ASTS", 'earnings_date': "19700101", 'strike_value_start': 1.5, 'strike_value_end': 1.8}
    ]

    fetcher = LowDeltaOptionFetcher()
    fetcher.process_tickers(stocks, action_type="cc")
