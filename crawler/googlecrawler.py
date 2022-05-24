import requests
from PyPDF2 import PdfFileReader
import traceback
import joblib
from joblib import Parallel, delayed
import contextlib
from tqdm import tqdm
import fitz
import io
import sys
from multiprocessing import Manager
from pathlib import Path
from .searcher import Serper
from .utils import *

@contextlib.contextmanager
def tqdm_joblib(tqdm_object):
    """Context manager to patch joblib to report into tqdm progress bar given as argument"""
    class TqdmBatchCompletionCallback(joblib.parallel.BatchCompletionCallBack):
        def __call__(self, *args, **kwargs):
            tqdm_object.update(n=self.batch_size)
            return super().__call__(*args, **kwargs)

    old_batch_callback = joblib.parallel.BatchCompletionCallBack
    joblib.parallel.BatchCompletionCallBack = TqdmBatchCompletionCallback
    try:
        yield tqdm_object
    finally:
        joblib.parallel.BatchCompletionCallBack = old_batch_callback
        tqdm_object.close()

class Crawler:
  def __init__(self, searcher: Serper, required: list, das: list, is_colab: bool=False):
    self.searcher = searcher
    self.required = required
    self.das      = das
    self.is_colab = is_colab

  def fast_response(self, url: str):
    headers = {
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0',
    }
    response = requests.get(url, headers=headers, timeout=5)
    response.encoding = 'utf-8'
    if response.status_code >= 400:
      response.close()
      return None
    else:
      content = response.content
      response.close()
      return content

  def search(self, params: dict={'query': '', 'type': 'article'}, num_result: int=40, num_page: int=1) -> list:
    urls = []
    for req in self.required:
      for da in self.das:
        count_page = 1
        q = f'{req} + "{da}"{params["query"]}'
        print(q)
        pages = self.searcher.normal(q, num_result)

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

          count_page += 1
          if count_page > num_page: break
    return urls

  def collect(self, search_urls: list, project_name: str, crawl_type: str='article'):
    if self.is_colab:
      crawl_folder = Path.cwd().parents[0].joinpath(f'drive/MyDrive/Colab Notebooks/crawl_data/{project_name}')
    else:
      crawl_folder = Path.cwd().joinpath(f'{project_name}')
    crawltype_folder = crawl_folder.joinpath(f'{crawl_type}')
    crawltype_folder.mkdir(parents=True, exist_ok=True)

    required_name = ' - '.join([r.replace('"', '') for r in self.required])
    required_folder = crawltype_folder.joinpath(f'{required_name}')
    required_folder.mkdir(parents=True, exist_ok=True)

    current_folder = create_folder(required_folder)
    current_folder.mkdir(parents=True, exist_ok=True)

    all_urls = f'[{today}] {crawl_type}.txt'
    check_file(all_urls)
    with open(all_urls, 'a') as fw:
      for url in search_urls:
        fw.write(f'{url["url"]} -{url["date"]}\n')

    with open(all_urls, 'r') as fr:
      urls = [{'url': line.strip().split(' -')[0], 'date': line.strip().split(' -')[1]} for line in fr.readlines()]

    seen = set()
    urls_info = []
    print(f'Total = {len(urls)}')
    for url in urls:
      if url['url'] in seen: continue
      seen.add(url['url'])
      counter = urls.count(url)
      urls_info.append({
        'url'    : url['url'],
        'counter': counter,
        'date'   : url['date'],
      })
    urls_sort = (sorted(urls_info, key = lambda k: -k['counter']))
    return current_folder, urls_sort, required_name

class PDFCrawler(Crawler):
  def __init__(self, searcher: Serper, required: list, das: list, is_colab: bool=False):
    super().__init__(searcher, required, das, is_colab)
    self.params = {
      'query': ' filetype:pdf',
      'type' : 'pdf',
    }

  def pdf_search(self, num_result: int=40):
    return super().search(self.params, num_result)

  def get_info(self, current_folder, temp: list, i: int, url: str):
    try:
      content = super().fast_response(url['url'])
      if content == None: return

      with io.BytesIO(content) as f:
        reader = PdfFileReader(f)
        num_page = reader.getNumPages()
        info = reader.getDocumentInfo()

      pdf_info = {
        'url'       : url['url'],
        'counter'   : url['counter'],
        'num_page'  : int(num_page),
        'title'     : info.title if info != None else '',
        'date'      : url['date'],
        'num_img'   : 0,
        'total_size': 0,
      }
      
      if pdf_info['title'] == '' or info.title == None:
        file_save = f'{i+1}'
      else:
        file_save = f'{i+1} - {pdf_info["title"].replace("?","").replace(":","-")}'
      file_location = f'{current_folder}/{file_save}.pdf'
      pdf_info['location'] = f'{file_save}.pdf'

      with open(file_location, 'wb') as fw:
        fw.write(content)
      
      pdf_file = fitz.open(file_location)
      for page_index in range(len(pdf_file)):
        page = pdf_file[page_index]
        for img_info, img in zip(page.get_image_info(), page.get_images()):
          if img_info['height'] < 100 or img_info['width'] < 100: continue
          base_image = pdf_file.extract_image(img[0])
          pdf_info['num_img']    += 1
          pdf_info['total_size'] += sys.getsizeof(base_image['image'])
      pdf_info['img_ratio' ] = pdf_info['num_img']/pdf_info['num_page']
      pdf_info['size_ratio'] = pdf_info['total_size']/(pdf_info['num_img'] + 1e-6)
      temp.append(pdf_info)
    except Exception:
      print('\nget_info ==========================================')
      print(traceback.format_exc())
      print('========================================================\n')
      return

  def pdf_collect(self, project_name: str, num_result: int=40, num_final: int=30):
    search_urls = self.pdf_search(num_result)
    current_folder, urls_sort, required_name = super().collect(search_urls, project_name, self.params['type'])
    crawl_folder = current_folder.parents[0]
    temp_folder = Path.cwd().joinpath('temp')
    temp_folder.mkdir(parents=True, exist_ok=True)

    manager = Manager()
    temp = manager.list()

    length = min(num_final, len(urls_sort))
    with tqdm_joblib(tqdm(total=length)) as progress_bar:
      Parallel(n_jobs=-1, verbose=0)(delayed(self.get_info)(temp_folder, temp, i, url) for i, url in enumerate(urls_sort[:length]))

    temp_modified = [{f'{k}_normalized': t[k]/(max([te[k] for te in temp]) + 1e-6) for k in t.keys() if k not in ['url', 'title', 'date', 'location']} for t in temp]
    for tm, te in zip(temp_modified, temp):
      for k in te.keys():
        tm[k] = te[k]
      features = [tm[f'{k}_normalized'] for k in ['total_size', 'counter', 'num_page', 'num_img', 'img_ratio', 'size_ratio']]
      weights  = [0.3, 0.3, 0.1, 0.1, 0.1, 0.1]
      tm['score'] = sum([w*f for w,f in zip(weights, features)])

    # urls_sort = (sorted(temp, key = lambda k: (-k['counter'], -k['num_page'])))
    urls_sort = (sorted(temp_modified, key = lambda k: -k['score']))

    stats_file = f'{crawl_folder}/[{today}] {required_name} - stats report.txt'
    check_file(stats_file)

    with open(stats_file, 'a') as fw:
      out_text = ''
      for i, url in enumerate(urls_sort):
        if url['title'] == '' or url['title'] == None:
          file_save = f'{i+1}.pdf'
        else:
          file_save = f'{i+1} - {url["title"].replace("?","").replace(":","-")}.pdf'
        file_location = temp_folder.joinpath(url['location'])
        _ = file_location.rename(Path.cwd().joinpath(current_folder).joinpath(file_save))
        out_text += f'{i+1}. '
        if url['title'] != None:
          out_text += f'{url["title"]} '
        if url['date'] == '':
          out_text += stats_output(url) + '\n\n'
          # out_text += f'({url["url"]})\nCounter : {url["counter"]}\nPage num: {url["num_page"]}\n\n'
        else:
          out_text += stats_output(url) + f'Date       : {url["date"]}\n\n'
          # out_text += f'({url["url"]})\nCounter : {url["counter"]}\nPage num: {url["num_page"]}\nDate    : {url["date"]}\n\n'
      fw.write(out_text)
    return current_folder, stats_file