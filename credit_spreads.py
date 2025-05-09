from option_base import OptionBase
from datetime import datetime
import traceback

class CallSpreadFetcher(OptionBase):
    def fetch_put_options_with_low_delta(self, ticker_symbol, stock_price, earnings_date, strike_value_start, strike_value_end):
        try:
            # Fetch all option contracts in one go
            contracts = self.fetch_options_data(
                ticker_symbol,
                stock_price,
                option_type='C',
                strike_value_start=strike_value_start,
                strike_value_end=strike_value_end
            )

            # Use delayed-frozen market data (live frozen market)
            self.ib.reqMarketDataType(4)

            # Request snapshot market data for all contracts at once
            market_data = {}
            for contract in contracts:
                ticker = self.custom_reqMktData(contract)
                # ticker = self.ib.reqMktData(contract, '', snapshot=True)
                # self.ib.sleep(15)
                market_data[contract] = ticker

            # Log received data and cancel requests
            for contract, ticker in market_data.items():
                self.logger.info(f"{contract.localSymbol}: bid={ticker.bid}, ask={ticker.ask}")
                self.ib.cancelMktData(contract)
                self.ib.sleep(2)

            # Organize contracts by expiry
            contracts_by_expiry = {}
            for contract in contracts:
                expiry = contract.lastTradeDateOrContractMonth
                contracts_by_expiry.setdefault(expiry, []).append(contract)

            # Evaluate spreads using cached market_data
            for expiry, contract_list in contracts_by_expiry.items():
                strikes = sorted(c.strike for c in contract_list)
                strike_to_contract = {c.strike: c for c in contract_list}

                for i, long_strike in enumerate(strikes):
                    for short_strike in strikes[i+1:]:
                        spread = short_strike - long_strike
                        if spread <= 0:
                            continue

                        long_contract = strike_to_contract[long_strike]
                        short_contract = strike_to_contract[short_strike]

                        long_ticker = market_data.get(long_contract)
                        short_ticker = market_data.get(short_contract)
                        if not long_ticker or not short_ticker:
                            continue

                        ask_long = long_ticker.ask
                        bid_short = short_ticker.bid

                        if ask_long is None or bid_short is None or ask_long == 0:
                            continue

                        net_debit = ask_long - bid_short
                        if net_debit <= 0:
                            continue

                        return_multiple = spread / net_debit
                        obj = {
                            'ticker': ticker_symbol,
                            'stockPrice': stock_price,
                            'expiration': expiry,
                            'longStrike': long_strike,
                            'shortStrike': short_strike,
                            'spread': spread,
                            'askLong': ask_long,
                            'bidShort': bid_short,
                            'netDebit': net_debit,
                            'returnMultiple': return_multiple,
                        }
                        self.data.append(obj)
                        self.logger.info(f"CONTRACT PASSES: {obj}")

        except Exception:
            self.logger.error(f"Error fetching call spread for {ticker_symbol}: {traceback.format_exc()}")

if __name__ == "__main__":
    tickers = [
        {'symbol': 'HIMS', 'earnings_date': '19700101', 'strike_value_start': 60, 'strike_value_end': 75},
        {'symbol': 'RKLB', 'earnings_date': '19700101', 'strike_value_start': 35, 'strike_value_end': 41},
        {'symbol': 'SOFI', 'earnings_date': '19700101', 'strike_value_start': 20, 'strike_value_end': 15}
    ]

    fetcher = CallSpreadFetcher()
    fetcher.process_tickers(tickers, action_type="c")
