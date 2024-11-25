#!/usr/bin/env python
# coding: utf-8

# Option chains
# =======

# In[1]:


from ib_insync import *
util.startLoop()

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=12)


# Suppose we want to find the options on the SPX, with the following conditions:
# 
# * Use the next three monthly expiries;
# * Use strike prices within +- 20 dollar of the current SPX value;
# * Use strike prices that are a multitude of 5 dollar.

# To get the current market value, first create a contract for the underlyer (the S&P 500 index):

# In[2]:


stock = Stock('AAPL', 'SMART', 'USD')
ib.qualifyContracts(stock)


# To avoid issues with market data permissions, we'll use delayed data:

# In[3]:


ib.reqMarketDataType(3)


# Then get the ticker. Requesting a ticker can take up to 11 seconds.

# In[4]:


[ticker] = ib.reqTickers(stock)
ticker


# Take the current market value of the ticker:

# In[5]:


aplValue = ticker.marketPrice()
print(aplValue)


# The following request fetches a list of option chains:

# In[6]:


chains = ib.reqSecDefOptParams(stock.symbol, '', stock.secType, stock.conId)
print(util.df(chains))


# These are four option chains that differ in ``exchange`` and ``tradingClass``. The latter is 'SPX' for the monthly and  'SPXW' for the weekly options. Note that the weekly expiries are disjoint from the monthly ones, so when interested in the weekly options the monthly options can be added as well.
# 
# In this case we're only interested in the monthly options trading on SMART:

# In[7]:


chain = next(c for c in chains if c.tradingClass == 'AAPL' and c.exchange == 'SMART')
# print(chain)


# # What we have here is the full matrix of expirations x strikes. From this we can build all the option contracts that meet our conditions:

# # In[8]:


strikes = chain.strikes
expirations = sorted(exp for exp in chain.expirations)[:3]
rights = ['P']

contracts = [Option('AAPL', expiration, strike, right, 'SMART', tradingClass='AAPL')
        for right in rights
        for expiration in expirations
        for strike in strikes]

contracts = ib.qualifyContracts(*contracts)
len(contracts)

print(contracts[0])

# # In[9]:


# contracts[0]


# # Now to get the market data for all options in one go:

# # In[10]:


# tickers = ib.reqTickers(*contracts)

# tickers[0]


# # The option greeks are available from the ``modelGreeks`` attribute, and if there is a bid, ask resp. last price available also from ``bidGreeks``, ``askGreeks`` and ``lastGreeks``. For streaming ticks the greek values will be kept up to date to the current market situation.

# # In[11]:


# ib.disconnect()
