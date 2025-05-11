from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import TickAttrib
import threading
import time

class IBapi(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.option_data = {}  # Store option data here
        
    def tickPrice(self, reqId, tickType, price, attrib: TickAttrib):
        if tickType == 1:  # Bid price
            if reqId not in self.option_data:
                self.option_data[reqId] = {'bid': None, 'ask': None}
            self.option_data[reqId]['bid'] = price
            print(f"ReqId {reqId}: Bid price updated to {price}")
        elif tickType == 2:  # Ask price
            if reqId not in self.option_data:
                self.option_data[reqId] = {'bid': None, 'ask': None}
            self.option_data[reqId]['ask'] = price
            print(f"ReqId {reqId}: Ask price updated to {price}")
            
    def tickSnapshotEnd(self, reqId: int):
        print(f"Snapshot ended for ReqId {reqId}")
        print(f"Final data for ReqId {reqId}: {self.option_data.get(reqId, {})}")

def run_loop():
    app.run()

def create_contract(symbol, sec_type, exchange, currency, last_trade_date=None, strike=None, right=None):
    contract = Contract()
    contract.symbol = symbol
    contract.secType = sec_type
    contract.exchange = exchange
    contract.currency = currency
    if last_trade_date:
        contract.lastTradeDateOrContractMonth = last_trade_date
    if strike:
        contract.strike = strike
    if right:
        contract.right = right
    return contract

# Create and connect the app
app = IBapi()
app.connect('127.0.0.1', 7497, 123)  # TWS demo account port is 7497, IB Gateway is 4001

# Start the socket in a thread
api_thread = threading.Thread(target=run_loop, daemon=True)
api_thread.start()

time.sleep(1)  # Give time for connection to establish

if not app.isConnected():
    print("Failed to connect to TWS")
    exit()

# Example: Fetch prices for a few RKLB options
# First, let's get the next expiry (you might want to automate this)
next_expiry = "20250516"  # Replace with actual expiry date you want to check

# Create option contracts for different strikes (example strikes)
strikes = [20, 21, 22]
req_id = 1

for strike in strikes:
    # Create call option contract
    call_contract = create_contract(
        symbol='RKLB',
        sec_type='OPT',
        exchange='SMART',
        currency='USD',
        last_trade_date=next_expiry,
        strike=strike,
        right='C'
    )
    app.reqMktData(req_id, call_contract, "", True, False, [])
    req_id += 1
    
    # Create put option contract
    put_contract = create_contract(
        symbol='RKLB',
        sec_type='OPT',
        exchange='SMART',
        currency='USD',
        last_trade_date=next_expiry,
        strike=strike,
        right='P'
    )
    app.reqMktData(req_id, put_contract, "", True, False, [])
    req_id += 1

# Let the data come in
print("Waiting for market data...")
time.sleep(10)  # Wait for 10 seconds to collect data

# Print final collected data
print("\nFinal option data collected:")
for req_id, data in app.option_data.items():
    print(f"Request ID {req_id}: Bid={data['bid']}, Ask={data['ask']}")

# Disconnect
app.disconnect()