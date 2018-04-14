from matplotlib import pyplot as plt
import pandas as pd
import pandas.tools.plotting as pdplot
from statsmodels.tsa.arima_model import ARIMA
from sklearn.metrics import mean_squared_error
from statsmodels.graphics.tsaplots import plot_pacf, plot_acf
from mongoObjects import CollectionManager
from putAndGetData import create_timeseries



class ArimaModel(object):
    def __init__(self,p,d,q,ticker):
        self.p = p
        self.d = d
        self.q = q
        self.ticker = ticker

    def plot_timeseries(self,series):
        plt.plot(range(1, len(series) + 1), series)
        plt.title(self.ticker)
        plt.savefig('plots/ARIMA/{0}.pdf'.format(self.ticker))
        plt.show()

    def plot_autocorr(self,series):
        plot_acf(series,lags=range(0,2500,50),alpha=0.9)
        plt.title(self.ticker + ' Autocorrelation Plot')
        plt.savefig('plots/ARIMA/{0}Autocor.pdf'.format(self.ticker))
        plt.close()

    def plot_partial_autocorr(self,series):
        plot_pacf(series, lags=range(0,2500,50),alpha=0.9)
        plt.title(self.ticker + ' Partial Autocorrelation')
        plt.savefig('plots/ARIMA/{0}ParAutocor.pdf'.format(self.ticker))
        plt.close()

    def plot_residuals(self,series):
        model = ARIMA(series, order=(self.p, self.d, self.q))
        model_fit = model.fit(disp=0)
        print(model_fit.summary())

        residuals = pd.DataFrame(model_fit.resid)
        residuals.plot()
        plt.title(self.ticker + ' ARIMA residuals')
        plt.savefig('plots/ARIMA/{0}Resid_{1}{2}{3}.pdf'.format(self.ticker,self.p,self.d,self.q))
        plt.close()
        print(residuals.describe())

    def fit(self,train):
        model = ARIMA(train, order=(self.p, self.d, self.q))
        model_fit = model.fit(disp=0)
        output = model_fit.forecast()
        nextDaysPred = output[0][0]
        return nextDaysPred

    def fit_and_plot(self, series, dates, window=0):
        size = len(dates) - 518
        train, test = series[0:size], series[size:len(series)]
        predictions = list()
        w = 0
        for t in range(len(test) + 1):
            model = ARIMA(train, order=(self.p, self.d, self.q))
            model_fit = model.fit(disp=0)
            output = model_fit.forecast()
            yhat = output[0][0]
            predictions.append(yhat)
            obs = yhat
            if w == window and t != len(test):
                train.append(test[t])
                w = 0
            else:
                train.append(obs)
                w += 1

        error = mean_squared_error(test, predictions[:len(test)])
        print(error)
        actual, days = create_timeseries(manager, self.ticker)
        days = [days[x] for x in range(0, len(days), 2)]
        actual = [actual[y] for y in range(0, len(actual), 2)]
        predictions = [predictions[p] for p in range(0,len(predictions),2)]

        plt.plot(days, actual, color='black', label='Actual')
        plt.plot(days[1000:], predictions[:-1], color='red', label='LSTM predictions')
        plt.xlabel('day')
        plt.title(self.ticker)
        plt.ylabel('price')
        plt.legend(loc=2)
        plt.savefig('plots/ARIMA/ARIMA_{0}_predictions.pdf'.format(self.ticker))
        plt.show()


if __name__ == '__main__':
    stock = 'vz'
    manager = CollectionManager('5Y_technicals', 'AlgoTradingDB')
    model = ArimaModel(1,1,0,stock)
    data = create_timeseries(manager,stock)[0]
    model.fit_and_plot(data,create_timeseries(manager,stock)[1])