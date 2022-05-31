from serpapi import GoogleSearch
from crawler.utils import *

class Serper:
  def __init__(self, engine: str):
    self.engine = engine
  
  def get_api(self):
    self.api_key = ''

  def search(self, q: str, num_result: int=None, tbs: str=None):
    # self.get_api()
    params = {
      'engine' : self.engine,
      'api_key': self.api_key,
      'q'      : q,
      'num'    : num_result,
    }
    if tbs != None: params['tbs'] = tbs
    search = GoogleSearch(params)
    pages  = search.pagination()
    return pages

  def normal(self, q: str, num_result: int=40, back: int=2, has_tbs: bool=True):
    if has_tbs:
      year = int(date.today().strftime('%Y')) - back
      tbs  = f'cdr%3A1%2Ccd_min%3A01-01-{year}%2Ccd_max%3A'
    else:
      tbs  = None 
    return self.search(q, num_result, tbs)