from urllib import request
from serpapi import GoogleSearch
from crawler.utils import *
import random

class Serper:
  def __init__(self, engine: str, parameters: dict):
    self.engine     = engine
    self.parameters = parameters
    self.api_keys   = self.parameters['api_keys']

  def account_info(self, api_url):
    response = requests.get(api_url)
    return response.json()

  def check_api(self, api_key: str, all_searches: list):
    info = self.account_info(f'https://serpapi.com/account?api_key={api_key}')
    try:
      all_searches.append(info['total_searches_left'])
    except KeyError:
      print(api_key)
  
  def get_total_searches(self):
    manager = Manager()
    all_searches = manager.list()
    print('\n')
    with tqdm_joblib(tqdm(desc='Checking API...', total=len(self.api_keys))) as _:
      Parallel(n_jobs=-1, verbose=0)(delayed(self.check_api)(api_key, all_searches) for api_key in self.api_keys)
    return sum(all_searches)

  def search(self, q: str, num_result: int=None, tbs: str=None):
    api_keys = []
    for key in self.api_keys:
      info = self.account_info(f'https://serpapi.com/account?api_key={key}')
      if info['total_searches_left'] > 0:
        api_keys.append(key)
    api_key = random.choice(api_keys)
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