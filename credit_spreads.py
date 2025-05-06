from option_base import OptionBase
from datetime import datetime, timedelta
import logging

RETURN_THRESHOLD = 10.0  # Minimum return threshold (10x)
RETURN_TOTAL_DAYS = 255  # Example expiry days for calculation

class CallSpreadFetcher(OptionBase):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

    def fetch_call_spread(self, ticker_symbol, expiry_date, target_strike):
        """
        Fetch call spread options for a given ticker, expiry date, and target strike.
        Buy the strike just below target_strike and sell at target_strike.
        Check for 10x return on premium paid.
        """
        try:
            # Get current stock price
            stock_price = self.get_stock_price(ticker_symbol)
            self.logger.info(f"Current stock price for {ticker_symbol}: {stock_price}")

            # Convert expiry date to the required format
            expiry_date_dt = datetime.strptime(expiry_date, '%Y%m%d')
            days_till_expiration = (expiry_date_dt - datetime.today()).days + 1
            if days_till_expiration <= 0:
                self.logger.error("Expiry date must be in the future.")
                return

            # Fetch option chain for the specific expiry
            stock = Stock(ticker_symbol, 'SMART', 'USD')
            self.ib.qualifyContracts(stock)

            chains = self.ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
            if not chains:
                self.logger.info(f"No options chains available for {ticker_symbol}.")
                return

            chain = next((c for c in chains if c.tradingClass == ticker_symbol and c.exchange == 'CBOE'), None)
            if not chain:
                self.logger.info(f"No suitable chain found for {ticker_symbol}.")
                return

            # Check if the expiry date is available
            if expiry_date not in chain.expirations:
                self.logger.info(f"Expiry date {expiry_date} not available for {ticker_symbol}.")
                return

            # Find the strike just below the target strike
            strikes = sorted([s for s in chain.strikes if s <= target_strike])
            if len(strikes) < 2:
                self.logger.info(f"Not enough strikes available below {target_strike} for {ticker_symbol}.")
                return
            buy_strike = strikes[-2]  # Second highest strike below target_strike
            sell_strike = target_strike

            # Fetch option contracts
            contracts = [
                Option(stock.symbol, expiry_date, buy_strike, 'C', 'SMART'),
                Option(stock.symbol, expiry_date, sell_strike, 'C', 'SMART')
            ]
            contracts = self.ib.qualifyContracts(*contracts)
            if len(contracts) != 2:
                self.logger.info(f"Could not qualify both contracts for {ticker_symbol}.")
                return

            self.ib.reqMarketDataType(4)  # Delayed data
            buy_contract, sell_contract = contracts

            # Get market data
            market_data_buy = self.ib.reqMktData(buy_contract, '', snapshot=True)
            market_data_sell = self.ib.reqMktData(sell_contract, '', snapshot=True)
            self.ib.sleep(10)  # Wait for data

            # Extract prices
            buy_ask = market_data_buy.ask if market_data_buy.ask > 0 else None
            sell_bid = market_data_sell.bid if market_data_sell.bid > 0 else None

            self.ib.cancelMktData(buy_contract)
            self.ib.cancelMktData(sell_contract)
            self.ib.sleep(2)

            if not buy_ask or not sell_bid:
                self.logger.info(f"Invalid market data for {ticker_symbol}: Buy ask={buy_ask}, Sell bid={sell_bid}")
                return

            # Calculate spread and premium
            spread = (sell_strike - buy_strike) * 100  # Spread value in dollars
            premium_paid = (buy_ask - sell_bid) * 100  # Net premium paid
            if premium_paid <= 0:
                self.logger.info(f"Invalid premium calculation for {ticker_symbol}: Premium={premium_paid}")
                return

            # Calculate return
            return_ratio = spread / premium_paid
            percentage_return = (return_ratio - 1) * 100  # Net return percentage

            self.logger.info(f"Call Spread for {ticker_symbol}: Buy {buy_strike}, Sell {sell_strike}, Spread=${spread}, Premium=${premium_paid}, Return={return_ratio:.2f}x")

            # Store data if return exceeds threshold
            if return_ratio >= RETURN_THRESHOLD:
                obj = {
                    'ticker': ticker_symbol,
                    'stockPrice': stock_price,
                    'expiration': expiry_date,
                    'buyStrike': buy_strike,
                    'sellStrike': sell_strike,
                    'premiumPaid': premium_paid,
                    'spreadValue': spread,
                    'returnRatio': return_ratio,
                    'percentageReturn': percentage_return,
                    'DTE': days_till_expiration,
                    'buyAskPrice': buy_ask,
                    'sellBidPrice': sell_bid,
                }
                self.data.append(obj)
                self.logger.info(f"High return spread found for {ticker_symbol}: {return_ratio:.2f}x")

        except Exception as e:
            self.logger.error(f"Error processing {ticker_symbol}: {e}")
            import traceback
            traceback.print_exc()

    def post_processing(self):
        """
        Notify for spreads with return >= 10x.
        """
        import sys
        sys.path.append('../common')
        import common_utils

        keys_to_keep = [
            'ticker',
            'stockPrice',
            'expiration',
            'buyStrike',
            'sellStrike',
            'premiumPaid',
            'spreadValue',
            'returnRatio',
            'percentageReturn',
            'DTE',
        ]

        for data_obj in self.data:
            if data_obj['returnRatio'] >= RETURN_THRESHOLD:
                filtered_data = {key: data_obj[key] for key in keys_to_keep if key in data_obj}
                filtered_data['action'] = 'call_spread'
                message = "\n".join([f"{key}: {value}" for key, value in filtered_data.items()])
                common_utils.notify_message_aleph(f"High Return Call Spread:\n{message}")
                self.logger.info(f"Notified for {data_obj['ticker']}: {data_obj['returnRatio']:.2f}x return")

    def process_tickers(self, tickers):
        """
        Process a list of tickers with expiry date and target strike.
        """
        self.action_type = 'call_spread'
        self.connect()
        for ticker in tickers:
            self.logger.info(f"Processing ticker: {ticker['symbol']}")
            self.fetch_call_spread(
                ticker['symbol'],
                ticker['expiry_date'],
                ticker['target_strike']
            )
        self.disconnect()
        self.save_to_excel()
        self.post_processing()

if __name__ == "__main__":
    # Example tickers
    tickers = [
        {
            'symbol': 'HIMS',
            'expiry_date': (datetime.now() + timedelta(days=255)).strftime('%Y%m%d'),
            'target_strike': 100.0
        },
    ]

    fetcher = CallSpreadFetcher()
    fetcher.process_tickers(tickers)