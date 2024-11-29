from option_base import OptionBase
from volatile_tickers import volatile_tickers

TARGET_DELTA = 0.3
TARGET_PROFIT = 50

class CreditSpreadsFetcher(OptionBase):
    def fetch_put_options_with_low_delta(self, ticker_symbol):
        contracts = self.fetch_options_data(
            ticker_symbol,
            expiry_start=25,
            expiry_end=47
        )

        contracts_with_marketdata = []
        self.ib.reqMarketDataType(4)
        for contract in contracts:
            market_data = self.ib.reqMktData(contract, '', snapshot=True)
            self.ib.sleep(10)
            self.logger.info(market_data)
            self.ib.cancelMktData(contract)
            self.ib.sleep(2)

            if market_data.modelGreeks:
                contracts_with_marketdata.append({
                    "contract_obj": contract,
                    "marketdata": market_data
                })

        for current_contract in contracts_with_marketdata:
            bid_price = current_contract["marketdata"].bid
            delta = current_contract["marketdata"].modelGreeks.delta

            if delta and abs(delta) < TARGET_DELTA:
                self.logger.info("CONTRACT PASSES")
                obj = {
                    'ticker': ticker_symbol,
                    'delta': delta,
                    'bid_price': bid_price
                }
                self.data.append(obj)


if __name__ == "__main__":
    fetcher = CreditSpreadsFetcher()
    fetcher.process_tickers(volatile_tickers)
