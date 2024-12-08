import requests
import datetime


cookies = {
    'device_t': 'c2hVdkJROjA.fqdqymWZWaUgBubuvoNo9xkn5LI_AQ967G4gCI0lPvs',
    'sessionid': 'au95x3rohqiq3geieyjsdebolyw8uo7l',
    'sessionid_sign': 'v3:w9bWxfqlh15Eo0Uf6NdhDm2RLM7Sy40G8zymhCDAeFY=',
    'tv_ecuid': 'f9957390-cd5c-4d53-a0bd-06ce8be3799f',
    '_ga': 'GA1.1.1796500685.1732297490',
    'cookiesSettings': '{"analytics":true,"advertising":true}',
    'cookiePrivacyPreferenceBannerProduction': 'accepted',
    '_sp_ses.cf1a': '*',
    '__eoi': 'ID=394f9e905017f1b6:T=1732296226:RT=1733593864:S=AA-AfjZMdpcir-tsattF6axcw17J',
    '_ga_YVVRYGL0E0': 'GS1.1.1733591724.24.1.1733593931.60.0.0',
    '_sp_id.cf1a': '77242685-c027-4bfa-9c62-4e34759c3738.1731939397.19.1733593990.1733504920.f7c75eb7-0fb9-4d3a-b3d4-0afc17ac3834.452a5a77-4a8b-427e-a421-277deec4ef2b.cfb32268-3edf-484b-b0a9-4b44055e82e7.1733591724530.78',
}

headers = {
    'accept': 'application/json',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'text/plain;charset=UTF-8',
    # 'cookie': 'device_t=c2hVdkJROjA.fqdqymWZWaUgBubuvoNo9xkn5LI_AQ967G4gCI0lPvs; sessionid=au95x3rohqiq3geieyjsdebolyw8uo7l; sessionid_sign=v3:w9bWxfqlh15Eo0Uf6NdhDm2RLM7Sy40G8zymhCDAeFY=; tv_ecuid=f9957390-cd5c-4d53-a0bd-06ce8be3799f; _ga=GA1.1.1796500685.1732297490; cookiesSettings={"analytics":true,"advertising":true}; cookiePrivacyPreferenceBannerProduction=accepted; _sp_ses.cf1a=*; __eoi=ID=394f9e905017f1b6:T=1732296226:RT=1733593864:S=AA-AfjZMdpcir-tsattF6axcw17J; _ga_YVVRYGL0E0=GS1.1.1733591724.24.1.1733593931.60.0.0; _sp_id.cf1a=77242685-c027-4bfa-9c62-4e34759c3738.1731939397.19.1733593990.1733504920.f7c75eb7-0fb9-4d3a-b3d4-0afc17ac3834.452a5a77-4a8b-427e-a421-277deec4ef2b.cfb32268-3edf-484b-b0a9-4b44055e82e7.1733591724530.78',
    'origin': 'https://www.tradingview.com',
    'priority': 'u=1, i',
    'referer': 'https://www.tradingview.com/',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}

params = {
    'label-product': 'screener-stock',
}

data = '{"columns":["name","description","logoid","update_mode","type","typespecs","close","pricescale","minmov","fractional","minmove2","currency","change","volume","market_cap_basic","fundamental_currency_code","price_earnings_ttm","earnings_per_share_diluted_ttm","earnings_per_share_diluted_yoy_growth_ttm","dividends_yield_current","sector.tr","market","sector","recommendation_mark","Volatility.D","earnings_release_next_trading_date_fq","exchange"],"filter":[{"left":"change","operation":"less","right":-2},{"left":"market_cap_basic","operation":"egreater","right":200000000000}],"ignore_unknown_fields":false,"options":{"lang":"en"},"range":[0,200],"sort":{"sortBy":"market_cap_basic","sortOrder":"desc"},"symbols":{},"markets":["america"],"filter2":{"operator":"and","operands":[{"operation":{"operator":"or","operands":[{"operation":{"operator":"and","operands":[{"expression":{"left":"type","operation":"equal","right":"stock"}},{"expression":{"left":"typespecs","operation":"has","right":["common"]}}]}},{"operation":{"operator":"and","operands":[{"expression":{"left":"type","operation":"equal","right":"stock"}},{"expression":{"left":"typespecs","operation":"has","right":["preferred"]}}]}},{"operation":{"operator":"and","operands":[{"expression":{"left":"type","operation":"equal","right":"dr"}}]}},{"operation":{"operator":"and","operands":[{"expression":{"left":"type","operation":"equal","right":"fund"}},{"expression":{"left":"typespecs","operation":"has_none_of","right":["etf"]}}]}}]}}]}}'

def run():
    response = requests.post('https://scanner.tradingview.com/america/scan', params=params, cookies=cookies, headers=headers, data=data)
    response_json = response.json()['data']

    adapted_final_object = []
    for object in response_json:
        if object['d'][24] is None:
            future_date = datetime.datetime.utcnow() + datetime.timedelta(days=10 * 365)
            earnings_date = future_date.strftime('%Y%m%d')
        else:
            earnings_date = datetime.datetime.utcfromtimestamp(object['d'][24]).strftime('%Y%m%d')
        adapted_final_object.append({
            'symbol': object['d'][0],
            'earnings_date': earnings_date
        })

    return adapted_final_object
