#this code is based on
# 1. https://builtin.com/data-science/portfolio-optimization-python
# 2. https://flask.palletsprojects.com/en/2.2.x/quickstart/#a-minimal-application

from flask import Flask
from flask import request
import pandas_datareader.data as web
import pandas as pd
from datetime import datetime
from functools import reduce
from pypfopt.expected_returns import mean_historical_return
from pypfopt.risk_models import CovarianceShrinkage
from pypfopt.efficient_frontier import EfficientFrontier
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from flask_cors import CORS

pd.set_option('display.max_columns', None)
pd.set_option('display.max_rows', None)

app = Flask(__name__)
CORS(app)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


def get_stock(ticker):
    start = datetime(2019,10,15)
    end = datetime(2021,10,15)

    data = web.DataReader(ticker,"yahoo",start=start,end=end)
    data[ticker] = data["Close"]
    data = data[ticker]
    print(data.head())
    return data

def combine_stocks(tickers):
    data_frames = []
    for ticker in tickers:
        data_frames.append(get_stock(ticker))

    df_merged = reduce(lambda  left,right: pd.merge(left,right,on=['Date'], how='outer'), data_frames)
    print(df_merged.head())
    return df_merged

def calc_effient_mean_variance_optimization(tickers, value):
  portfolio = combine_stocks(tickers)
  mu = mean_historical_return(portfolio)
  S = CovarianceShrinkage(portfolio).ledoit_wolf()
  ef = EfficientFrontier(mu, S)
  weights = ef.max_sharpe()

  cleaned_weights = ef.clean_weights()
  print(dict(cleaned_weights))
  ef.portfolio_performance(verbose=True)
  latest_prices = get_latest_prices(portfolio)
  da = DiscreteAllocation(weights, latest_prices, total_portfolio_value=value)

  allocation, leftover = da.greedy_portfolio()
  print("Discrete allocation:", allocation)
  print("Funds remaining: ${:.2f}".format(leftover))
  allocations = {}
  allocations["discrete"] = allocation
  allocations["weights"] = dict(cleaned_weights)
  return allocations

from pypfopt import HRPOpt

def calc_effient_hierarchical_risk_Parity(tickers):
  portfolio = combine_stocks(tickers)
  returns = portfolio.pct_change().dropna()
  hrp = HRPOpt(returns)
  hrp_weights = hrp.optimize()
  hrp.portfolio_performance(verbose=True)
  print(dict(hrp_weights))
  latest_prices = get_latest_prices(portfolio)
  da_hrp = DiscreteAllocation(hrp_weights, latest_prices, total_portfolio_value=100000)

  allocation, leftover = da_hrp.greedy_portfolio()
  print("Discrete allocation (HRP):", allocation)
  print("Funds remaining (HRP): ${:.2f}".format(leftover))

from pypfopt.efficient_frontier import EfficientCVaR
def calc_effient_mean_conditional_value_at_risk(tickers):
  portfolio = combine_stocks(tickers)
  S = portfolio.cov()
  ef_cvar = EfficientCVaR(mu, S)
  cvar_weights = ef_cvar.min_cvar()

  cleaned_weights = ef_cvar.clean_weights()
  print(dict(cleaned_weights))
  da_cvar = DiscreteAllocation(cvar_weights, latest_prices, total_portfolio_value=100000)

  allocation, leftover = da_cvar.greedy_portfolio()
  print("Discrete allocation (CVAR):", allocation)
  print("Funds remaining (CVAR): ${:.2f}".format(leftover))


@app.route("/", methods=['POST'])
def post_me():
    error = None
    # example how to detect method
    if request.method == 'POST':
      print('POST')
    # Examples how to read parameter
    #
    # if valid_login(request.form['username'],
    #   request.form['password']):
    #     return log_the_user_in(request.form['username'])
    # else:
    #   error = 'Invalid username/password'
    #
    # Example reading myltiple parameters
    #
    # request.form.getlist('username[]')
    allocations = calc_effient_mean_variance_optimization(request.form.getlist('tickers[]'), float(request.form['value']))
    return allocations
    #return "<p>post, me! " + ''.join(map(str, request.form.getlist('username[]'))) +"</p>"

def main():
        calc_effient_mean_variance_optimization(['AAPL', 'GOOG'])

if __name__ == "__main__":
    main()