import time
from datetime import datetime

import requests


def arlotime_to_time(timestamp):
    return timestamp / 1000


def time_to_arlotime(timestamp=None):
    if timestamp is None:
        timestamp = time.time()
    return int(timestamp * 1000)


def arlotime_to_datetime(timestamp):
    return datetime.fromtimestamp(int(timestamp / 1000))


def http_to_datetime(http_timestamp):
    return datetime.strptime(http_timestamp, '%a, %d %b %Y %H:%M:%S GMT')


def now_strftime(date_format='%Y-%m-%dT%H:%M:%S'):
    return datetime.now().strftime(date_format)


def arlotime_strftime(timestamp, date_format='%Y-%m-%dT%H:%M:%S'):
    # date_format = '%Y-%m-%dT%H:%M:%S'
    return arlotime_to_datetime(timestamp).strftime(date_format)


def http_get(url, filename=None):
    """Download HTTP data."""
    try:
        ret = requests.get(url)
    except requests.exceptions.SSLError:
        return False
    except Exception:
        return False

    if ret.status_code != 200:
        return False

    if filename is None:
        return ret.content

    with open(filename, 'wb') as data:
        data.write(ret.content)
    return True


def http_get_img(url):
    """Download HTTP data."""
    if url is None:
        return None, None

    try:
        ret = requests.get(url)
    except requests.exceptions.SSLError:
        return None, None
    except Exception:
        return None, None

    if ret.status_code != 200:
        return None, None

    date = ret.headers.get('Last-Modified', None)
    if date is not None:
        date = http_to_datetime(date)
    else:
        date = datetime.now()
    return ret.content, date


def http_stream(url, chunk=4096):
    """Generate stream for a given record video.

    :param url: url of stream to read
    :param chunk: chunk bytes to read per time
    :returns generator object
    """
    ret = requests.get(url, stream=True)
    ret.raise_for_status()
    for data in ret.iter_content(chunk):
        yield data
