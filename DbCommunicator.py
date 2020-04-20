from cassandra.cluster import Cluster
from cassandra import ReadTimeout
import uuid
import datetime
cluster = Cluster(contact_points=['172.17.0.2'],port=9042)
session = cluster.connect()

# create db if not exists
def initDB():
    queryToCreateTables = [
        "CREATE KEYSPACE forecaster WITH REPLICATION ={'class' : 'SimpleStrategy', 'replication_factor' : 1};",
        "create if not exists table forecaster.users (id UUID PRIMARY KEY, username text, password text, salt text, apiKey text);",
        "create if not exists table forecaster.stocks (name text primary key, price_at_time map<timestamp, float>, lastFetch timestamp);",
        "create if not exists table forecaster.stock_in_profile (id UUID , stock_name text, primary key (id, stock_name));"
    ]
    for query in queryToCreateTables:
        prepared_query = session.prepare(query)
        session.execute_async(prepared_query)
    # create if not exists table forecaster.logs (id UUID, operation text, count int, primary key(id, operation));

# given username returns user or None
def getUser(username):
    query = """select * from forecaster.users where username = '{}' ALLOW FILTERING""".format(username)
    future = session.execute_async(query)
    try:
        rows = future.result()
        try:
            user = rows[0]
            return user
        except IndexError:
            print('User does not exist')
    except ReadTimeout:
        print('Could not connect to DB, try again later')

# given stockName returns stock or None
def getStock(stockName):
    query = """select * from forecaster.stocks where name = '{}' ALLOW FILTERING""".format(stockName)
    future = session.execute_async(query)
    try:
        rows = future.result()
        try:
            stock = rows[0]
            return stock
        except IndexError:
            print('Stock does not exist')
    except ReadTimeout:
        print('Could not connect to DB, try again later')

# given uid, and stockName checks if is in clients profile, return true is true, or False, or None if error communicating
def hasProfileStock(uid, stockName):
    query = """select * from forecaster.stock_in_profile where id = ? AND stock_name = ? ALLOW FILTERING"""
    prepared_query = session.prepare(query)
    future = session.execute_async(prepared_query, [uid, stockName])
    try:
        rows = future.result()
        try:
            stock = rows[0]
            return True
        except IndexError:
            print('Stock does not exist')
            return False
    except ReadTimeout:
        print('Could not connect to DB, try again later')

# given uid, returns users stocks
def getUserStocks(uid):
    query = """select stock_name from forecaster.stock_in_profile where id = ? ALLOW FILTERING"""
    prepared_query = session.prepare(query)
    future = session.execute_async(prepared_query, [uid])
    try:
        rows = future.result()
        try:
            stocks = []
            for row in rows:
                stocks.append(row.stock_name)
            return stocks
        except IndexError:
            print('Stock does not exist')
    except ReadTimeout:
        print('Could not connect to DB, try again later')

# adds stockData, to the stock
def addStockToDB(stockName, stockData):
    query = """
            UPDATE forecaster.stocks
            SET price_at_time = ?, lastFetch = ?
            WHERE name = ?;"""
    prepared_query = session.prepare(query)
    session.execute(prepared_query, [stockData, datetime.datetime.now(), stockName])

# adds uid and stockname
def addStockToProfile(uid, stockName):
    query = """
            INSERT INTO forecaster.stock_in_profile (id, stock_name)
            VALUES (?, ?)
            """
    prepared_query = session.prepare(query)
    session.execute(prepared_query, [uid, stockName])

# returns user from providedAPi key or None
def getUserFromKey(apiKey):
    query = """select * from forecaster.users where apiKey = '{}' ALLOW FILTERING""".format(apiKey)
    future = session.execute_async(query)
    try:
        rows = future.result()
        try:
            user = rows[0]
            return user
        except IndexError:
            print('User does not exist')
    except ReadTimeout:
        print('Could not connect to DB while getting user Id')

# given, uid, stockname removes from user profile
def removeStockFromProfile(uid, stockName):
    query = """
            Delete from forecaster.stock_in_profile where id=? AND stock_name=?;
            """
    prepared_query = session.prepare(query)
    session.execute(prepared_query, [uid, stockName])

# creates user, given username, password, salt and apiKey
def createUser(username, password, salt, key):
    query = """
            INSERT INTO forecaster.users (id, username, password, salt, apikey)
            VALUES (?, ?, ?, ?, ?)
            """
    prepared_query = session.prepare(query)
    session.execute(prepared_query, [uuid.uuid1(), username, password, salt, key])
