import hashlib
import random
import string
import datetime
from matplotlib.figure import Figure

def getHashedPassword(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode('UTF-8'), salt, 100000)

def key_generator(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def create_figure(title, yValues, xValues):
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    xs = xValues
    ys = yValues
    axis.plot(xs, ys)
    return fig

def formatStringToDatetime(date):
    try:
        datetime_object = datetime.datetime.strptime(date, '%Y-%m-%d')
        return datetime_object
    except TypeError:
        print('No date given')
        return None