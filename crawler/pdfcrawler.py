from crawler.generalcrawler import Crawler
from crawler.searcher import Serper
from crawler.utils import *

from joblib import Parallel, delayed
from multiprocessing import Manager
import shutil

class PDFCrawler(Crawler):
  def __init__(self, searcher: Serper, required: list, das: list, is_colab: bool=False):
    super().__init__(searcher, required, das, is_colab)
    self.params = {
      'query': ' filetype:pdf',
      'type' : 'pdf',
    }

  def pdf_search(self, num_result: int=40):
    return super().search(self.params, num_result)
    
  def get_info_pdf(self, current_folder, urls_processing, i: int, url: dict):
    super().get_info(current_folder, urls_processing, i, url, False)
  
  def save_pdf(self, current_folder, urls_sort, required_name: str='', num_final: int=30):
    crawl_folder = current_folder.parents[0]
    temp_folder = crawl_folder.joinpath('temp')
    temp_folder.mkdir(parents=True, exist_ok=True)

    manager = Manager()
    urls_processing = {
      'pdf'  : manager.list(),
      'doc'  : manager.list(),
      'error': manager.list(),
    }

    # length = min(num_final, len(urls_sort))
    length = len(urls_sort)
    with tqdm_joblib(tqdm(total=length)) as _:
      Parallel(n_jobs=-1, verbose=0)(delayed(self.get_info_pdf)(temp_folder, urls_processing, i, url) for i, url in enumerate(urls_sort[:length]))

    temp_modified = [{f'{k}_normalized': t[k]/(max([te[k] for te in urls_processing['pdf']]) + 1e-6) for k in t.keys() if k not in ['url', 'title', 'date', 'location']} for t in urls_processing['pdf']]
    for tm, te in zip(temp_modified, urls_processing['pdf']):
      for k in te.keys():
        tm[k] = te[k]
      features = [tm[f'{k}_normalized'] for k in ['total_size', 'counter', 'num_page', 'num_img', 'img_ratio', 'size_ratio']]
      weights  = [0.1, 0.5, 0.1, 0.1, 0.1, 0.1]
      tm['score'] = tm['num_img_normalized']*tm['counter_normalized']*sum([w*f for w,f in zip(weights, features)])

    urls_sort = (sorted(temp_modified, key = lambda k: (-k['score'], -k['counter'])))
    urls_sort = urls_sort[:min(num_final, len(urls_sort))]

    stats_file = current_folder.joinpath(f'{current_time} {required_name} - stats report.txt')
    check_file(stats_file)

    with open(stats_file, 'a') as fw:
      out_text = f'F0 keywords     = {", ".join(self.required)}\nDeck Attributes = {", ".join(self.das)}\n\n'
      for i, url in enumerate(urls_sort):
        if url['title'] == '' or url['title'] == None:
          file_save = f'{i+1}.pdf'
        else:
          file_save = f'{i+1} - {url["title"].replace("?","").replace(":","-").replace("/","-").replace("|","-")}.pdf'
          file_save = file_save.replace('\\', '-').replace('"', '').replace('\\n', '')
        file_location = temp_folder.joinpath(url['location'])
        _ = file_location.rename(Path.cwd().joinpath(current_folder).joinpath(file_save))
        out_text += f'{i+1}. '
        if url['title'] != None:
          out_text += f'{url["title"]} '
        if url['date'] == '':
          out_text += stats_output(url) + '\n\n'
        else:
          out_text += stats_output(url) + f'Date       : {url["date"]}\n\n'
      fw.write(out_text)
    if list(urls_processing['error']) != []:
      print('URL failed to get info:')
      for error_url in urls_processing['error']:
        print(error_url)
    shutil.rmtree(temp_folder)
    return current_folder, stats_file

  def pdf_collect(self, project_name: str, num_result: int=40, num_final: int=30):
    search_urls = self.pdf_search(num_result)
    current_folder, urls_sort, required_name = super().collect(search_urls, project_name, self.params['type'])
    return self.save_pdf(current_folder, urls_sort, required_name, num_final)