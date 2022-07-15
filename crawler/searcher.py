from urllib import request
from serpapi import GoogleSearch
from crawler.utils import *
import random

class Serper:
  def __init__(self, engine: str, parameters: dict):
    self.engine     = engine
    self.parameters = parameters
    self.api_keys   = self.parameters['api_keys']
    self.api_left   = {}

  def account_info(self, api_url):
    response = requests.get(api_url)
    return response.json()

  def check_api(self, left_keys, api_key: str):
    info = self.account_info(f'https://serpapi.com/account?api_key={api_key}')
    try:
      search_left = info['total_searches_left']
      if search_left > 0:
        left_keys.append((api_key, search_left))
      # searches['num'].append(info['total_searches_left'])
      # if info['total_searches_left'] > 0:
      #   searches['api'].append(api_key)
    except KeyError:
      print(api_key)
  
  def get_total_searches(self):
    print('\n')
    manager = Manager()
    left_keys = manager.list()
    with tqdm_joblib(tqdm(desc='Checking API...', total=len(self.api_keys))) as _:
      Parallel(n_jobs=-1, verbose=0)(delayed(self.check_api)(left_keys, api_key) for api_key in self.api_keys)

    for api_info in left_keys:
      self.api_left[api_info[0]] = api_info[1]

    return sum(self.api_left.values())

  def search(self, q: str, num_result: int=None, tbs: str=None):
    # api_keys = []
    # for key in self.api_keys:
    #   info = self.account_info(f'https://serpapi.com/account?api_key={key}')
    #   if info['total_searches_left'] > 0:
    #     api_keys.append(key)
    # api_key = random.choice(api_keys)

    api_keys = []
    for key in self.api_left.keys():
      if self.api_left[key] > 0:
        api_keys.append(key)
    api_key = random.choice(api_keys)
    self.api_left[api_key] -= 1

    # api_key = 'e1fb07044cb818d097595349e32a1ddebdb2aa520d294f21c85ec8a7f752395b'
    params = {
      'engine' : self.engine,
      'api_key': api_key,
      'q'      : q,
      'num'    : num_result,
    }
    if tbs != None: params['tbs'] = tbs
    search = GoogleSearch(params)
    pages  = search.pagination()
    return pages

  def normal(self, q: str, num_result: int=40, back: int=2, has_tbs: bool=True):
    self.year = int(date.today().strftime('%Y')) - back
    if has_tbs:
      tbs  = f'cdr%3A1%2Ccd_min%3A01-01-{self.year}%2Ccd_max%3A'
    else:
      tbs  = None 
    return self.search(q, num_result, tbs)