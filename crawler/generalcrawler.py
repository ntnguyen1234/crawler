import requests
from crawler.searcher import Serper
from crawler.converter import Converter
from crawler.utils import *
import urllib3
import urllib.parse
try:
  from scrapingbee import ScrapingBeeClient
except Exception:
  pass

class Crawler:
  def __init__(self, searcher: Serper, parameters: dict):
    self.searcher   = searcher
    self.parameters = parameters
    self.converter  = Converter(self.parameters)

  def crawl_pages(self, pages) -> list:
    urls = []
    for result in pages:
      print(f"Current page: {result['serpapi_pagination']['current']}\n")

      # Get original link result from search
      for organic_result in result["organic_results"]:
        url = {
          'url'  : urllib.parse.unquote_plus(organic_result['link']),
          'title': replace_name(organic_result['title'])
        }
        if 'date' in organic_result.keys():
          published_date = organic_result['date'].split(', ')[-1]
          if published_date.isnumeric():
            if int(published_date) < self.searcher.year: continue
            else: url['date'] = organic_result['date']
          else:
            url['date'] = ''
        else:
          url['date'] = ''
        urls.append(url)
      break
    return urls

  def search(self, query: str='', num_result: int=40) -> list:
    urls = []
    for req in self.parameters['required']:
      for da in self.parameters['das']:
        if self.parameters['das'][0] == '':
          q = f'{req}{query}'
        else:
          q = f'{req} "{da}"{query}'
        print(q)
        num_temp = num_result
        while num_temp >= 10:
          pages = self.searcher.normal(q, num_temp)
          urls_temp = self.crawl_pages(pages)
          print(len(urls_temp), num_temp)
          if len(urls_temp) == 0:
            num_temp -= 20
          else:
            num_temp = 0

        while len(urls_temp) == 0:
          if num_temp == 0 and num_result > 10:
            num_temp = 10
            pages = self.searcher.normal(q, num_temp)
            urls_temp = self.crawl_pages(pages)
            print(len(urls_temp), num_temp)
          else:
            pages = self.searcher.normal(q, num_temp, has_tbs=False)
            urls_temp = self.crawl_pages(pages)
            print(len(urls_temp), num_temp)
            break
        urls += urls_temp
        # pages = self.searcher.normal(q, num_result)
        # urls_temp = self.crawl_pages(pages, urls)
        # times = 0
        # while len(urls_temp) == 0:
        #   if times == 0:
        #     pages = self.searcher.normal(q, num_result=10)
        #   elif times == 1:
        #     pages = self.searcher.normal(q, num_result=num_result, has_tbs=False)
        #   elif times == 2:
        #     pages = self.searcher.normal(q, num_result=10, has_tbs=False)
        #   else: break
        #   urls_temp = self.crawl_pages(pages, urls)
        #   times += 1
    return urls

  def collect(self, search_urls: list, project_name: str, types: dict={'crawl_type': 'article'}):
    required_folder, required_name = set_folder(self.parameters, project_name, types['crawl_type'])
    
    all_urls = f'[{today}] {types["crawl_type"]}.txt'
    check_file(all_urls)
    with open(all_urls, 'a') as fw:
      for url in search_urls:
        fw.write(f'{url["url"]} -{url["date"]} -{url["title"]}\n')

    with open(all_urls, 'r') as fr:
      urls = [{'url': line.strip().split(' -')[0], 'date': line.strip().split(' -')[1], 'title': line.strip().split(' -')[2]} for line in fr.readlines()]

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

  def initialize_process(self, current_folder, types: dict={'crawl_type': 'article'}):
    temp_folder = current_folder.parents[0].joinpath('temp')
    if types['crawl_type'] != 'article':
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

  def get_info(self, urls_processing, i: int, url: dict, current_folder=None, types: dict={'crawl_type': 'article'}):
    try:
      final_url, content, content_text = self.fast_response(url['url'])
      if content == None: return
      else:
        if 'linkedin.com' in final_url: return
        url['url'] = final_url
        ppt_suffixes = ['.ppt?', '.ppt&', '.ppt#']
        pps_suffixes = ['.ppsx?', '.ppsx&', '.ppsx#']
        if content_text.startswith('%PDF-'):
          if types['crawl_type'] != 'article':
            pdf_info = readwrite_pdf(content, current_folder, i, url, self.parameters['filters'])
            urls_processing['pdf'].append(pdf_info)
        elif (content_text.startswith('PK') and not string_contain(url['url'], pps_suffixes, ['.ppsx'])) or string_contain(url['url'], ppt_suffixes, ['.ppt']):
          if types['crawl_type'] != 'article':
            ppt_info = self.converter.readwrite_ppt(content, content_text, current_folder, i, url)
            if ppt_info != None:
              urls_processing['ppt'].append(ppt_info)
        elif types['crawl_type'] == 'article':
          url['content']      = content
          url['content_text'] = content_text
          urls_processing['raw'].append(url)
    except Exception:
      urls_processing['error'].append(url)
      print(f'\n\nget_info ==========================================\n\n{url}\n\n')
      print(traceback.format_exc())
      print('========================================================\n')

  def process_urls(self, urls: list, project_name: str, types: dict={'crawl_type': 'article'}):
    current_folder, urls_sort, required_name = self.collect(urls, project_name, types)

    length = len(urls_sort)
    backend = 'loky'
    while True:
      try:
        temp_folder, urls_processing = self.initialize_process(current_folder, types)
        with tqdm_joblib(tqdm(desc='Processing URLs...', total=length)) as _:
          Parallel(n_jobs=-1, verbose=0, backend=backend)(delayed(self.get_info)(urls_processing, i, url, temp_folder, types) for i, url in enumerate(urls_sort[:length]))
        break
      except Exception:
        if backend == 'loky':
          backend = 'threading'
          continue
        else:
          temp_folder, urls_processing = self.initialize_process(current_folder)
          for i, url in tqdm(enumerate(urls_sort[:length]), desc='Processing URLs (slow)...', total=length):
            self.get_info(urls_processing, i, url, temp_folder, types)
          break
    for key in urls_processing.keys():
      urls_processing[key] = sort_urls(urls_processing[key])
    return current_folder, temp_folder, urls_processing, required_name

  def printing_error(self, urls_processing):
    if len(urls_processing['error']) > 0:
      print('URL failed to get info:')
      for error_url in urls_processing['error']:
        print(error_url)