import yfinance as yf
import numpy as np

def get_iv_rank(ticker):
    """
    Calculate the 52-week IV rank for a given stock ticker.
    
    :param ticker: Stock ticker symbol as a string
    :return: 52-week IV rank as a percentage
    """
    try:
        # Fetch the stock's options data
        stock = yf.Ticker(ticker)
        options_dates = stock.options

        if not options_dates:
            raise ValueError("No options data available for this ticker.")

        # Fetch implied volatilities for all expiration dates
        ivs = []
        for exp_date in options_dates:
            options_chain = stock.option_chain(exp_date)
            calls = options_chain.calls
            puts = options_chain.puts

            # Combine calls and puts for IV calculations
            combined_iv = list(calls['impliedVolatility']) + list(puts['impliedVolatility'])
            ivs.extend([iv for iv in combined_iv if not np.isnan(iv)])

        if not ivs:
            raise ValueError("No valid implied volatility data found.")

        # Calculate 52-week IV rank
        current_iv = np.mean(ivs)  # Assume current IV is the average of all options IV
        lowest_iv = min(ivs)
        highest_iv = max(ivs)

        iv_rank = (current_iv - lowest_iv) / (highest_iv - lowest_iv) * 100

        return {
            "ticker": ticker,
            "current_iv": current_iv,
            "lowest_iv": lowest_iv,
            "highest_iv": highest_iv,
            "iv_rank": iv_rank,
        }
    
    except Exception as e:
        return {"error": str(e)}

# Example usage
if __name__ == "__main__":
    ticker = input("Enter a stock ticker (e.g., AAPL, TSLA): ").upper()
    result = get_iv_rank(ticker)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"IV Rank for {ticker}:")
        print(f"  Current IV: {result['current_iv']:.2%}")
        print(f"  Lowest IV in 52 weeks: {result['lowest_iv']:.2%}")
        print(f"  Highest IV in 52 weeks: {result['highest_iv']:.2%}")
        print(f"  IV Rank: {result['iv_rank']:.2f}%")
