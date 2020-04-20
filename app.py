# __________                                            _____
# ___  ____/______ _____________ _____________ ___________  /______ ________
# __  /_    _  __ \__  ___/_  _ \_  ___/_  __ `/__  ___/_  __/_  _ \__  ___/
# _  __/    / /_/ /_  /    /  __// /__  / /_/ / _(__  ) / /_  /  __/_  /
# /_/       \____/ /_/     \___/ \___/  \__,_/  /____/  \__/  \___/ /_/
#
# Welcome to Forecaster!
# Forecaster is a restful api service designed by developer to developers.
# You can select your favourite stocks and get daily updates on their Price change,
# average weekly price, historical prices, min-max, and (soon-to-add) Forecasted Prediction!

import requests_cache
import os
import time
import io

from flask import Flask, request, jsonify, json, Response
from Utils import *
from DbCommunicator import *
from urllib.request import urlopen
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from cassandra.util import OrderedDict

requests_cache.install_cache('forcaster', backend='sqlite', expire_after=43200000)

app = Flask(__name__)

twentyFourHoursInMilli = 86400000
# initDB()


# function to register a user with the system,
# log him in, and provide the client with an api key.
# Will return 201 if everything goes smoothly, 400 if page is not found,
# and 422 if message request is malformed
# EXAMPLE:
# curl -i -H "Content-Type: application/json" -X POST -d '{"username":"mondi","password":"myPassword"}' http://0.0.0.0:80/login
@app.route('/login', methods=['POST'])
def create_a_user():
    if request.json is not None and request.method == "POST" and 'username' in request.json and 'password' in request.json:
        username = request.json['username']
        password = request.json['password']
        api_key = key_generator(64)
        user = getUser(username)
        salt = os.urandom(32)
        if user is None:
            createUser(username, str(getHashedPassword(password, salt).hex()), str(salt.hex()), api_key)
        elif user.password == getHashedPassword(password, bytes.fromhex(user.salt)).hex() and username == user.username:
            return jsonify({'message': 'Welcome back! Here is your api key: {}'.format(getUser(username).apikey)}), 201
        else:
            return jsonify('Ups smth went to sh.. bad!'), 400
        return jsonify({'message': 'Welcome to Forecaster! Here is your API SIGN KEY: {}'.format(api_key)}), 201
    else:
        return jsonify({'error': 'Message malformed!'}), 422



# Add or Delete stocks from client account - POST and Delete
# EXAMPLE
# curl -i -H "x-access-req: 7OVT9JMBFUEIOQT9V6OAZNIAJHG2PNFCMVTN8N66VMOTCVV1RU1D2N2GHCM0BUO8TGVH01WOGAYG45I5T3ZZUOPFDWDWNPYAHJ3STF51VWMHZW08W5B1VDA3YUNKTGXBRIKOG0FO9WLYFQSY92IEGFYSE0TPXAQSQ0W53HGNXEEUF0JJDFE64DHB7KHY868HYJS7IFZ490HJP710G58JBRZD1AWEO008FKMWTKCYU14H4R0YX7TF1BPG47GFR6O" -H "Content-Type: application/json" -X POST -d '{"stockName":"AAPL"}' http://0.0.0.0/profile/edit
@app.route('/profile/edit', methods=['POST', 'DELETE'])
def editProfile():
    apiKey = getApiKey(request.headers)
    if apiKey is not None and request.json is not None and 'stockName' in request.json:
        # fetch user
        user = getUserFromKey(apiKey)
        stockName = request.json['stockName']
        if request.method == "POST":
            if user.id is not None:
                # check if db has stock and is up to date
                stock = getStock(stockName)
                if stock is None or stock.lastfetch.timestamp() < time.time() - twentyFourHoursInMilli:
                    if fetchStockAndAddToDB(stockName) is 'error':
                        return jsonify({'error': 'Stock symbol not found'}), 404
                addStockToProfile(user.id, stockName)
                return jsonify({'message': '{0} added to your favourites!'.format(stockName)}), 201
            else:
                return jsonify({'error': 'API KEY NOT FOUND'}), 404
        elif request.method == 'DELETE':
            removeStockFromProfile(user.id, stockName)
            return jsonify({'message': 'DONE'}), 200
        else:
            return jsonify({'error': 'Malformed request follow the docs'}), 422
    else:
        return jsonify({'error': 'Unauthorized request or Malformed Message'}), 402

# function to get stock infrormation from users favourite stocks
# image will be returned
# returns response code 200 for success
# return 422 if message is malformed
# returns error request is not authenticated
# EXAMPLE
# http://0.0.0.0/stock/chart/AAPL?apiKey=7OVT9JMBFUEIOQT9V6OAZNIAJHG2PNFCMVTN8N66VMOTCVV1RU1D2N2GHCM0BUO8TGVH01WOGAYG45I5T3ZZUOPFDWDWNPYAHJ3STF51VWMHZW08W5B1VDA3YUNKTGXBRIKOG0FO9WLYFQSY92IEGFYSE0TPXAQSQ0W53HGNXEEUF0JJDFE64DHB7KHY868HYJS7IFZ490HJP710G58JBRZD1AWEO008FKMWTKCYU14H4R0YX7TF1BPG47GFR6O

@app.route('/stock/chart/<stockName>', methods=['GET'])
def getChart(stockName):
    apiKey = request.args.get('apiKey')
    if apiKey is not None and stockName is not None:
        user = getUserFromKey(apiKey)
        if user is not None:
            if hasProfileStock(user.id, stockName):
                stock = getStock(stockName)
                if stock is not None:
                    date = []
                    price = []
                    print(type(stock.price_at_time))
                    om = (OrderedDict)(stock.price_at_time)
                    for key in om.keys():
                        date.append(key)
                        price.append(om.get(key))
                    fig = create_figure('', price, date)
                    fig_out = io.BytesIO()
                    FigureCanvas(fig).print_png(fig_out)
                    return Response(fig_out.getvalue(), mimetype='image/png')
                else:
                    return jsonify({'message': 'Success!'}), 200
            else:
                return jsonify({'error': 'Malformed message!!'}), 422
        else:
            return jsonify({'error': 'Client could not be verified, please add correct API KEY'}), 402
    else:
        return jsonify({'error': 'Malformed message!'}), 422


# funciton to get summary of user stocks from start date, and end date (or none)
# Example
# http://0.0.0.0/stock/AAPL?apiKey=7OVT9JMBFUEIOQT9V6OAZNIAJHG2PNFCMVTN8N66VMOTCVV1RU1D2N2GHCM0BUO8TGVH01WOGAYG45I5T3ZZUOPFDWDWNPYAHJ3STF51VWMHZW08W5B1VDA3YUNKTGXBRIKOG0FO9WLYFQSY92IEGFYSE0TPXAQSQ0W53HGNXEEUF0JJDFE64DHB7KHY868HYJS7IFZ490HJP710G58JBRZD1AWEO008FKMWTKCYU14H4R0YX7TF1BPG47GFR6O&startDate=2018-01-01
@app.route('/stock/<stockName>', methods=['GET'])
def getStockSummary(stockName):
    apiKey = request.args.get('apiKey')
    startDate = formatStringToDatetime(request.args.get('startDate'))
    endDate = formatStringToDatetime(request.args.get('endDate'))
    if apiKey is not None and stockName is not None:
        user = getUserFromKey(apiKey)
        if user is not None:
            if hasProfileStock(user.id, stockName):
                stock = getStock(stockName)
                if stock is not None:
                    date = []
                    price = []
                    om = (OrderedDict)(stock.price_at_time)
                    for key in om.keys():
                        if startDate is not None:
                            if(key >= startDate):
                                date.append(key)
                                price.append(om.get(key))
                            else:
                                continue
                        if endDate is not None:
                            if(key < endDate):
                                date.append(key)
                                price.append(om.get(key))
                            else:
                                continue
                        date.append(key)
                        price.append(om.get(key))
                    minPrice = min(price)
                    maxPrice = max(price)
                    lastClosePrice = price[-1]
                    lastWeekAvg = sum(price[-7:])/7

                    # output = '<h1>Stock Name: {}</h1>'.format(stockName)
                    # output += '<h3>Last Close Price: {}</h1>'.format(lastClosePrice)
                    # output += '<h3>Min Price: {}</h1>'.format(minPrice)
                    # output += '<h3>Max Price: {}</h1>'.format(maxPrice)
                    # output += '<h3>Last week Average: {}</h1>'.format(lastWeekAvg)
                    # return output
                    return jsonify({'stock':'{0}'.format(stockName),
                                    'lastPrice':'{1}'.format(lastClosePrice),
                                    'minPrice':'{2}'.format(minPrice),
                                    'maxPrice':'{3}'.format(maxPrice),
                                    'weeklyAvgPrice':'{4}'.format(lastWeekAvg)}), 201
                else:
                    return jsonify({'error': 'Malformed message!'}), 422
            else:
                return jsonify({'error': 'Malformed message!'}), 422
        else:
            return jsonify({'error': 'Unauthorized Access!'}), 402
    else:
        return jsonify({'error': 'Malformed message!'}), 422


# function return all user stocks
# returns 402, 200, and 422 as in other requests (see above req)
# http://0.0.0.0/profile?apiKey=7OVT9JMBFUEIOQT9V6OAZNIAJHG2PNFCMVTN8N66VMOTCVV1RU1D2N2GHCM0BUO8TGVH01WOGAYG45I5T3ZZUOPFDWDWNPYAHJ3STF51VWMHZW08W5B1VDA3YUNKTGXBRIKOG0FO9WLYFQSY92IEGFYSE0TPXAQSQ0W53HGNXEEUF0JJDFE64DHB7KHY868HYJS7IFZ490HJP710G58JBRZD1AWEO008FKMWTKCYU14H4R0YX7TF1BPG47GFR6O
@app.route('/profile', methods=['GET'])
def getProfileSummary():
    apiKey = request.args.get('apiKey')
    if apiKey is not None:
        user = getUserFromKey(apiKey)
        if user is not None:
            # get all stocks of user
            # output = '<h1>Profile: {}</h1>'.format(user.username)
            # output += '<h3>Stocks: {}</h3>'.format(getUserStocks(user.id))
            # return output
            return jsonify({'stocks':'{0}'.format(getUserStocks(user.id))}), 201
            # print stocks as a json file
        else:
            return jsonify({'error': 'Unauthorized Access!'}), 402
    else:
        return jsonify({'error': 'Malformed message!'}), 422

@app.route('/', methods=['GET'])
def hello():
    return """"<!-- #######  YAY, I AM THE SOURCE EDITOR! #########--> <h1><span style="color: #5e9ca0;">Welcome to &nbsp;</span><span style="color: #2b2301;"><span style="caret-color: #2b2301;">Forecaster</span></span><span style="color: #5e9ca0;">!</span></h1> <h3><span style="color: #000000;">Forecaster is a restful api service designed by developer to developers.</span></h3> <h3><span style="color: #000000;">You can select your favourite stocks and get daily updates on their Price change,&nbsp;average weekly price, historical prices, min-max, and (soon-to-add) Forecasted Prediction!</span></h3> <h2 style="color: #2e6c80;">How to use Forecaster:</h2> <h4>Step 1.&nbsp;</h4> <p>Sign up! Its really easy, just send a post request to this website using your username and selected password. You will be given an API key... keep it a secret thought <img src="https://html-online.com/editor/tinymce4_6_5/plugins/emoticons/img/smiley-wink.gif" alt="wink" />&nbsp;shhhhh!!!&nbsp;</p> <p>ex:&nbsp;</p> <h4><strong><span style="color: #003300;">curl -i -H "Content-Type: application/json" -X POST -d '{"username":"John Smith","password":"Secret123"}' <a href="http://forcaster/login">http://forcaster/login</a></span></strong></h4> <h4><strong><span style="color: #003300;">&nbsp;</span></strong></h4> <h4>Step 2.&nbsp;</h4> <p>Add your favourite stocks or delete (-X DELETE) them to keep track of... Google, Apple, DowJones, Go.Ku Inc, NASDAQ etc.</p> <p>ex:</p> <h4><span style="color: #003300;"><strong>curl -i -H "x-access-req: &lt;APIkey&gt;" -H "Content-Type: application/json" -X POST -d '{"stockName":"AAPL"}' <a href="http://forecaster/profile/edit">http://forecaster/profile/edit</a></strong></span></h4> <h4><strong><span style="color: #003300;">&nbsp;</span></strong></h4> <h4>Step 3.&nbsp;</h4> <p>Start making calls to get your stock infromation. Just make sure to put your api-key as follows into the get request. You can also put a <strong>startDate</strong> and/or a <strong>endDate.&nbsp;</strong>This request will generate a json with: <strong>maxPrice, minPrice, AverageWeeklyPrice, currentPrice.</strong></p> <p><strong>ex:</strong></p> <p><a href="http://0.0.0.0/stock/AAPL?apiKey=&lt;APIkey&gt;&amp;startDate=2018-01-01">http:/forecaster/stock/AAPL?apiKey=&lt;APIkey&gt;&amp;startDate=2018-01-01</a></p> <p><br /><br /><strong>Step 4.</strong><br />Hate numbers like graphics? No problem, we'll return you a graph image <img src="https://html-online.com/editor/tinymce4_6_5/plugins/emoticons/img/smiley-wink.gif" alt="wink" /></p> <p>ex:</p> <p><a href="http://forecaster/stock/chart/AAPL?apiKey=&lt;APIkey&gt;">http://forecaster/stock/chart/AAPL?apiKey=&lt;APIkey&gt;</a><br /><br /><strong>Step 5.</strong><br />You can also have a look at your portolio. The following will return a json list of your favourite stocks.</p> <p><br />ex:</p> <pre>http://0.0.0.0/profile?apiKey=&lt;APIkey&gt;</pre> <p><br /><strong>Enjoy!</strong></p> <p><strong>&nbsp;</strong></p>"""


###################################
# financialmodelingprep.com QUERY #
###################################
def fetchStockAndAddToDB(stockName):
    url = "https://financialmodelingprep.com/api/v3/historical-price-full/" + stockName.upper()
    stock = getJsonparsedData(url)
    stockData = {}
    try:
        for s in stock['historical']:
            date = s['date']
            datetime_object = formatStringToDatetime(date)
            stockData[datetime_object] = s['close']
        addStockToDB(stockName, stockData)
        return 1
    except KeyError:
        print('wrong stock symbol')
        return 'error'

def getJsonparsedData(url):
    """
    Receive the content of ``url``, parse it as JSON and return the object.

    Parameters
    ----------
    url : str

    Returns
    -------
    dict
    """
    response = urlopen(url)
    data = response.read().decode("utf-8")
    return json.loads(data)

# get api key from header
def getApiKey(header):
    if header is not None and 'x-access-req' in header is not None:
        apiKey = request.headers['x-access-req']
    return apiKey

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)