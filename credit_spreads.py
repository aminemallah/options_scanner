from option_base import OptionBase
from volatile_tickers import volatile_tickers
from datetime import datetime

TARGET_DELTA = 0.25
TARGET_PROFIT = 50
EXPIRY_START = 2
EXPIRY_END = 20
RETURN_TOTAL_DAYS = 30

class CreditSpreadsFetcher(OptionBase):
    def fetch_put_options_with_low_delta(self, ticker_symbol, stock_price):
        contracts = self.fetch_options_data(
            ticker_symbol,
            stock_price,
            expiry_start=EXPIRY_START,
            expiry_end=EXPIRY_END
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

        for current_index in range(len(contracts_with_marketdata) - 1, -1, -1):
            current_contract = contracts_with_marketdata[current_index]
            current_contract_bid = current_contract["marketdata"].bid
            current_contract_delta = current_contract["marketdata"].modelGreeks.delta
            current_contract_exp = current_contract["contract_obj"].lastTradeDateOrContractMonth
            current_contract_strike = current_contract["contract_obj"].strike

            if current_contract_delta and abs(current_contract_delta) < TARGET_DELTA:
                for preceding_index in range(current_index - 1, -1, -1):
                    preceding_contract = contracts_with_marketdata[preceding_index]
                    preceding_contract_ask = preceding_contract["marketdata"].ask
                    preceding_contract_exp = preceding_contract["contract_obj"].lastTradeDateOrContractMonth
                    preceding_contract_strike = preceding_contract["contract_obj"].strike

                    expiration_date = datetime.strptime(preceding_contract_exp, '%Y%m%d')
                    days_till_expiration = (expiration_date - datetime.today()).days

                    spread = abs(current_contract_strike - preceding_contract_strike)
                    daily_premium = ((current_contract_bid - preceding_contract_ask)/days_till_expiration)*100
                    total_premium_collected = (current_contract_bid - preceding_contract_ask)*100
                    premiumInXDays = daily_premium * RETURN_TOTAL_DAYS
                    

                    if (current_contract_exp == preceding_contract_exp
                        and total_premium_collected >= (spread * 100) * 0.20):

                        obj = {
                            'ticker': ticker_symbol,
                            'stock_price': stock_price,
                            'expiration': current_contract_exp,
                            'bid_strike': current_contract["contract_obj"].strike,
                            'ask_strike': preceding_contract["contract_obj"].strike,
                            'delta': current_contract["marketdata"].modelGreeks.delta,
                            'impliedVolatility': current_contract["marketdata"].modelGreeks.impliedVol,
                            'lastPrice': current_contract["marketdata"].last,
                            'bid': current_contract["marketdata"].bid,
                            'ask': current_contract["marketdata"].ask,
                            f"percentageReturnPer{RETURN_TOTAL_DAYS}Days": premiumInXDays
                        }

                        self.logger.info("CONTRACT PASSES::")
                        self.logger.info(obj)
                        self.data.append(obj)

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
    fetcher = CreditSpreadsFetcher()
    fetcher.process_tickers(volatile_tickers)
