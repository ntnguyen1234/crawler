import requests
from crawler.searcher import Serper
from crawler.utils import *
import urllib3
from scrapingbee import ScrapingBeeClient

class Crawler:
  def __init__(self, searcher: Serper, parameters: dict):
    self.searcher   = searcher
    self.parameters = parameters

  def crawl_pages(self, pages, urls: list, num_page: int=1) -> list:
    urls_temp  = []
    count_page = 1
    for result in pages:
      print(f"Current page: {result['serpapi_pagination']['current']}\n")

      # Get original link result from search
      for organic_result in result["organic_results"]:
        url = {
          'url'  : organic_result['link'],
          'title': organic_result['title']
        }
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

  def search(self, query: str='', num_result: int=40, num_page: int=1) -> list:
    urls = []
    for req in self.parameters['required']:
      for da in self.parameters['das']:
        if self.parameters['das'][0] == '':
          q = f'{req}{query}'
        else:
          q = f'{req} "{da}"{query}'
        print(q)
        pages = self.searcher.normal(q, num_result)
        urls_temp = self.crawl_pages(pages, urls, num_page)
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
    required_folder, required_name = set_folder(self.parameters['is_colab'], project_name, crawl_type, self.parameters['required'])
    
    all_urls = f'[{today}] {crawl_type}.txt'
    check_file(all_urls)
    with open(all_urls, 'a') as fw:
      for url in search_urls:
        fw.write(f'{url["url"]} -{url["date"]} +{url["title"]}\n')

    with open(all_urls, 'r') as fr:
      urls = [{'url': line.strip().split(' -')[0], 'date': line.strip().split(' -')[1], 'title': line.strip().split(' +')[1]} for line in fr.readlines()]

    print(f'Total = {len(urls)}')
    urls_sort = sort_urls(urls)
    Path(all_urls).unlink()
    return required_folder, urls_sort, required_name

  def fast_response(self, url: str):
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0',
    }
    response = requests.get(url, headers=headers, timeout=30, allow_redirects=True, verify=False)
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
      return remove_trackings(final_url), content, content_text

  def scrapingbee(self, url: str):
    headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0',
    }
    client = ScrapingBeeClient(api_key=self.parameters['scrapingbee'])
    response = client.get(
      url,
      params = {
        'device'       : 'desktop',
        'block_ads'    : True,
        'json_response': True,
        'render_js'    : True,
        'window_width' : 1920,
        'window_height': 1080,
      },
      headers = headers,
    )
    res = json.loads(response.text)
    return res['body']

  def fallback_response(self, driver, url):
    retry = 0
    while retry < 3:
      try:
        driver.get(url)
        retry = 3
      except selenium.common.exceptions.WebDriverException:
        retry += 1
        if retry == 3: return None
        time.sleep(3)
    time.sleep(3)
    with open('test.html', 'w') as fw:
      fw.write(driver.page_source)
    out = BeautifulSoup(driver.page_source, 'lxml')
    return str(out)

  def initialize_process(self, current_folder, crawl_type: str='article'):
    temp_folder = current_folder.parents[0].joinpath('temp')
    if crawl_type != 'article':
      temp_folder.mkdir(parents=True, exist_ok=True)

    manager = Manager()
    urls_processing = {
      'raw'    : manager.list(),
      'doc'    : manager.list(),
      'pdf'    : manager.list(),
      'ppt'    : manager.list(),
      'error'  : manager.list(),
    }
    return temp_folder, urls_processing

  def get_info(self, urls_processing, i: int, url: dict, current_folder=None, crawl_type: str='article'):
    try:
      final_url, content, content_text = self.fast_response(url['url'])
      if content == None: return
      else:
        if 'linkedin.com' in final_url: return
        url['url'] = final_url
        if content_text.startswith('%PDF-'):
          if crawl_type != 'article':
            pdf_info = readwrite_pdf(content, current_folder, i, url)
            urls_processing['pdf'].append(pdf_info)
        elif content_text.startswith('PK') or url['url'].endswith('.ppt') or url['url'].contains('.ppt?') or url['url'].contains('.ppt&') or url['url'].contains('.ppt#'):
          if crawl_type != 'article':
            ppt_info = readwrite_ppt(content, content_text, current_folder, i, url)
            urls_processing['ppt'].append(ppt_info)
        else:
          url['content']      = content
          url['content_text'] = content_text
          urls_processing['raw'].append(url)
          
    except Exception:
      urls_processing['error'].append(url)
      print(f'\n\nget_info ==========================================\n\n{url}\n\n')
      print(traceback.format_exc())
      print('========================================================\n')

  def process_urls(self, urls: list, project_name: str, crawl_type: str='article'):
    current_folder, urls_sort, required_name = self.collect(urls, project_name, crawl_type)

    length = len(urls_sort)
    not_success = True
    backend = 'loky'
    while not_success:
      try:
        temp_folder, urls_processing = self.initialize_process(current_folder, crawl_type)
        with tqdm_joblib(tqdm(desc='Processing URLs...', total=length)) as _:
          Parallel(n_jobs=-1, verbose=0, backend=backend)(delayed(self.get_info)(urls_processing, i, url, temp_folder, crawl_type) for i, url in enumerate(urls_sort[:length]))
        not_success = False
      except Exception:
        if backend == 'loky':
          backend = 'threading'
        else:
          temp_folder, urls_processing = self.initialize_process(current_folder)
          for i, url in tqdm(enumerate(urls_sort[:length]), desc='Processing URLs (slow)...', total=length):
            self.get_info(urls_processing, i, url, temp_folder)
          not_success = False
        continue
    for key in urls_processing.keys():
      urls_processing[key] = sort_urls(urls_processing[key])
    return current_folder, temp_folder, urls_processing, required_name

  def printing_error(self, urls_processing):
    if len(urls_processing['error']) > 0:
      print('URL failed to get info:')
      for error_url in urls_processing['error']:
        print(error_url)