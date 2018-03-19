from mongoObjects import CollectionManager, MongoClient
from strategy import Strategy
from agent import InvestorAgent
from arima import ArimaModel
from putAndGetData import avg_price_timeseries, create_timeseries
import argparse
import utils
import warnings
from LSTM import NN


class Environment(object):
    def __init__(self, manager: CollectionManager, agent: InvestorAgent, startDay: int):
        self.timeperiod = manager.dates()
        self.manager = manager
        self.agent = agent
        self.day = startDay
        self.currentDate = self.timeperiod[self.day]

    def increment_day(self, strategy):
        self.day += 1
        self.currentDate = self.timeperiod[self.day]
        strategy.currentDate = self.timeperiod[self.day]

    def update_total_assets(self, agent: InvestorAgent):
        liquid = agent.capital_t
        investments = []
        for pos in agent.positions:
            pos.update_investment(agent, self.currentDate)
            investments.append(pos.currentInvestment)
        agent.update_assets(sum(investments) + liquid)


def trade(loss, statsModel, p, sharePer, startDate, startingCapital, stop, ticker, epochs,neurons,plotting=False):
    warnings.filterwarnings("ignore")
    """Initialize Environment"""
    # Data
    manager = CollectionManager('5Y_technicals', MongoClient()['AlgoTradingDB'])

    # Time
    dates = manager.dates()
    currentDate = startDate
    startDay = dates.index(currentDate)
    stopDay = dates.index(stop)
    bar = utils.ProgressBar(stopDay - startDay)

    results = {'p': p, 'sharePer': sharePer}

    # Predictive Model
    if statsModel == 'Arima':
        model = ArimaModel(1, 1, 0, ticker)
    if statsModel == 'LSTM':
        percent = startDay/len(dates)
        model = NN(create_timeseries(manager,ticker)[0],percent)
        batch_size = 1
        model.fit_lstm(batch_size, epochs, neurons)

    # Investor, Strategy and Trading Environment
    stopLoss = (1 - loss) * startingCapital
    tradingStrategy = Strategy(model, manager, ticker, currentDate, stopLoss, p)
    investor = InvestorAgent(startingCapital, tradingStrategy, startDay)
    environment = Environment(manager, investor, startDay)

    # Simulate Trading Environment
    bar.initialize()
    for d in range(startDay, stopDay):
        if len(investor.positions):
            for position in investor.positions:
                currentPrice = investor.check_price(environment.currentDate)
                actionDay = utils.laterDate(position.startDate,
                                            position.holdTime)  # Todo: hyperparameter? "patience"
                if environment.currentDate == actionDay or position.at_trigger_point(currentPrice):
                        position.sell(investor, currentPrice)

        T = investor.strategy.arithmetic_returns(5, environment.day)
        sig = investor.signal(T)
        if sig != 0:
            investor.strategy.make_position(investor, sig, environment.currentDate, stopLoss,
                                            sharePer)
            # if len(investor.positions)>1:
            #     for p in investor.positions[:-1]:
            #         if type(p) != type(investor.positions[-1]):
            #             p.sell(investor,currentPrice)
        environment.update_total_assets(investor)
        if d!= stopDay-1:
            environment.increment_day(investor.strategy)
        bar.progress()

    """PLOTTING"""
    actualPrice = avg_price_timeseries(manager, ticker, dates[startDay:stopDay])
    if not len(investor.capitalHistory):
        expReturn = 0
    else:
        expReturn = round(((investor.totalAssetHistory[len(
            investor.totalAssetHistory) - 1] - startingCapital) / startingCapital) * 100)
    gain = str(expReturn) + '%'

    possible = round(((actualPrice[-1] - actualPrice[0]) / actualPrice[0]) * 100, 1)
    mdd = utils.MDD(investor.totalAssetHistory)
    if plotting:
        utils.plot_capital(investor.totalAssetHistory, dates[startDay:stopDay], ticker, actualPrice, gain, mdd,
                           possible,model=statsModel)
    results['MDD'] = mdd
    results['return'] = expReturn
    results['possible'] = possible

    return (results)


if __name__ == '__main__':
    warnings.filterwarnings("ignore")

    """Arguments"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', choices=['Arima','LSTM'], metavar='M',
                        help='predictive model to use', default='Arima', required=False)  # Todo: add other choices
    parser.add_argument('--startDate', help='start date YYYY-MM-DD', default='2017-01-05', required=False, type=str)
    parser.add_argument('--startingCapital', help='amount of money to start with', default=5000.00, type=float,
                        required=False)
    parser.add_argument('--loss', help='percent of money you are willing to lose', default=.30, type=float,
                        required=False)
    parser.add_argument('--p', help='percent change to flag', default=0.03, type=float, required=False)
    parser.add_argument('--ticker', help='stock to consider', default='aapl', type=str, required=False)
    parser.add_argument('--sharePer', help='percent possible shares to buy', default=1.0, type=float, required=False)
    parser.add_argument('--stop', help='stop date YYYY-MM-DD', default='2018-02-05', required=False, type=str)
    parser.add_argument('--epochs',help='Number of Epochs for NN training',default=10,required=False,type=int)
    parser.add_argument('--neurons',help='Number of neurons',default=4,required=False,type=int)
    args = parser.parse_args()

    trade(args.loss, args.model, args.p, args.sharePer, args.startDate, args.startingCapital, args.stop, args.ticker,
          args.epochs,args.neurons,plotting=True)
