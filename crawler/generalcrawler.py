import requests
import traceback
from crawler.searcher import Serper
from crawler.utils import *

class Crawler:
  def __init__(self, searcher: Serper, required: list, das: list, is_colab: bool=False):
    self.searcher = searcher
    self.required = required
    self.das      = das
    self.is_colab = is_colab

  def crawl_pages(self, pages, urls: list, num_page: int=1):
    urls_temp = []
    count_page = 1
    for result in pages:
      print(f"Current page: {result['serpapi_pagination']['current']}\n")

      # Get original link result from search
      for organic_result in result["organic_results"]:
        url = {'url' : organic_result['link']}
        if 'date' in organic_result.keys():
          published_date = organic_result['date'].split(', ')[-1]
          if published_date.isnumeric():
            url['date'] = organic_result['date']
          else:
            url['date'] = ''
        else:
          url['date'] = ''
        urls.append(url)
        urls_temp.append(url)

      count_page += 1
      if count_page > num_page: break
    return urls_temp

  def search(self, params: dict={'query': '', 'type': 'article'}, num_result: int=40, num_page: int=1) -> list:
    urls = []
    for req in self.required:
      for da in self.das:
        q = f'{req} + "{da}"{params["query"]}'
        print(q)
        pages = self.searcher.normal(q, num_result)
        urls_temp = self.crawl_pages(pages, urls)
        times = 0
        while len(urls_temp) == 0:
          if times == 0:
            pages = self.searcher.normal(q, num_result=10)
          elif times == 1:
            pages = self.searcher.normal(q, num_result=10, has_tbs=False)
          else: break
          urls_temp = self.crawl_pages(pages, urls)
          times += 1
    return urls

  def collect(self, search_urls: list, project_name: str, crawl_type: str='article'):
    required_folder, required_name = set_folder(self.is_colab, project_name, crawl_type, self.required)
    
    all_urls = f'[{today}] {crawl_type}.txt'
    check_file(all_urls)
    with open(all_urls, 'a') as fw:
      for url in search_urls:
        fw.write(f'{url["url"]} -{url["date"]}\n')

    with open(all_urls, 'r') as fr:
      urls = [{'url': line.strip().split(' -')[0], 'date': line.strip().split(' -')[1]} for line in fr.readlines()]

    print(f'Total = {len(urls)}')
    urls_sort = sort_urls(urls)
    Path(all_urls).unlink()
    return required_folder, urls_sort, required_name

  def fast_response(self, url: str):
    headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0',
    }
    response = requests.get(url, headers=headers, timeout=(5, 30), allow_redirects=True)
    response.encoding = 'utf-8'
    if response.status_code >= 400:
      response.close()
      return None, None, None
    else:
      content = response.content
      content_text = response.text
      final_url = url
      for r in response.history:
        final_url = r.headers['Location']
      response.close()
      return final_url, content, content_text

  def get_info(self, current_folder, urls_processing, i: int, url: dict, not_parallel: bool=True):
    try:
      final_url, content, content_text = self.fast_response(url['url'])
      if content == None: return
      else:
        if 'linkedin.com' in final_url: return
        url['url'] = final_url
        if not content_text.startswith('%PDF-'):
          urls_processing['doc'].append(url)
        else:
            pdf_info = readwrite_pdf(content, current_folder, i, url)
            urls_processing['pdf'].append(pdf_info)
    except Exception:
      urls_processing['error'].append(url)
      print(url)
      print(f'\n\nget_info ==========================================\n url = {url} \n')
      print(traceback.format_exc())
      print('========================================================\n')