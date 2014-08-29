import urlparse
import oauth2 as oauth
import requests
import urllib

REQUEST_TOKEN_URL = 'http://localhost:8000/api/request_token/'
AUTHORIZE_TOKEN_URL = 'http://localhost:8000/api/authorize/'

CALLBACK_URL = 'http://example.com/request_token_ready'

def get_request_token(with_callback=True):
    consumer = oauth.Consumer(key='9fdce0e111a1489eb5a42eab7a84306b', secret='liqutXmqJpKmetfs')
    if with_callback:
        callback = CALLBACK_URL
    else:
        callback = 'oob'
    oauth_request = oauth.Request.from_consumer_and_token(consumer, http_url=REQUEST_TOKEN_URL, parameters={'oauth_callback': callback})
    oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, None)

    response = requests.get(REQUEST_TOKEN_URL, headers=oauth_request.to_header())
    request_token = dict(urlparse.parse_qsl(response.content))
    return request_token

def authorize_token(request_token):
    url = AUTHORIZE_TOKEN_URL + '?' + urllib.urlencode({'oauth_token': request_token['oauth_token']})
    return url

req_token = get_request_token()
url = authorize_token(req_token)
print "Please visit:"
print url