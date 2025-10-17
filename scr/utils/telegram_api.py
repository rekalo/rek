import http.client
import json
import urllib.parse
from ..data.config import TOKEN, BASE_URL

def get_updates(offset=None):
    try:
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/getUpdates?timeout=60"
        if offset:
            url += f"&offset={offset}"
        conn.request("GET", url)
        response = conn.getresponse()
        data = response.read().decode()
        return json.loads(data)
    except Exception as e:
        return {"result": []}

def send_message(chat_id, text, reply_markup=None):
    try:
        if len(text) > 4096:
            text = text[:4090] + "..."
            
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/sendMessage"
        params = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }
        
        if reply_markup:
            params['reply_markup'] = reply_markup
            
        headers = {'Content-type': 'application/json'}
        conn.request("POST", url, json.dumps(params), headers)
        response = conn.getresponse()
        return response.read()
    except Exception as e:
        return None

def edit_message_reply_markup(chat_id, message_id, reply_markup=None):
    try:
        conn = http.client.HTTPSConnection(BASE_URL)
        url = f"/bot{TOKEN}/editMessageReplyMarkup"
        params = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        
        if reply_markup:
            params['reply_markup'] = reply_markup
            
        headers = {'Content-type': 'application/json'}
        conn.request("POST", url, json.dumps(params), headers)
        response = conn.getresponse()
        return response.read()
    except Exception as e:
        return None

def fetch_url(url):
    try:
        parsed = urllib.parse.urlparse(url)
        conn = http.client.HTTPSConnection(parsed.netloc)
        path = parsed.path
        if parsed.query:
            path += '?' + parsed.query
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        
        if response.status == 200:
            return response.read().decode('utf-8', errors='ignore')
        else:
            return None
    except Exception as e:
        return None
