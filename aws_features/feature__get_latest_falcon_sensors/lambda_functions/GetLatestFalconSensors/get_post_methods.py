import urllib3, urllib.parse

retries = urllib3.Retry(total=5, connect=5, read=2, redirect=5, backoff_factor=5)
http = urllib3.PoolManager()

def get_method(url,headers=None):
    http=urllib3.PoolManager()
    r = http.request('GET', url=url, headers=headers, retries=retries)
    return r.data
    
def post_method(url, body=None, headers=None):
    http=urllib3.PoolManager()
    r = http.request('POST', url=url, headers=headers, body=body, retries=retries)
    return r.data