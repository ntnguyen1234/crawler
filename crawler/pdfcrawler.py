from dataclasses import replace
from crawler.generalcrawler import Crawler
from crawler.searcher import Serper
from crawler.utils import *

class PDFCrawler(Crawler):
  def __init__(self, searcher: Serper, parameters: dict):
    super().__init__(searcher, parameters)

  def pdf_collect(self, project_name: str, num_result: int=40, num_final: int=30):
    search_urls = super().search(' filetype:pdf', num_result)
    current_folder, temp_folder, urls_processing, required_name = super().process_urls(search_urls, project_name, 'pdf')
    return self.save_pdf(current_folder, temp_folder, urls_processing, required_name, num_final)
  
  def save_pdf(self, current_folder, temp_folder, urls_processing: dict, required_name: str, num_final: int=30):
    # current_folder, temp_folder, urls_processing, required_name = super().process_urls(search_urls, project_name, 'pdf')
    temp_modified = [{f'{k}_normalized': t[k]/(max([te[k] for te in urls_processing['pdf']]) + 1e-6) for k in t.keys() if k not in ['url', 'title', 'date', 'location']} for t in urls_processing['pdf']]
    for tm, te in zip(temp_modified, urls_processing['pdf']):
      for k in te.keys():
        tm[k] = te[k]
      features = [tm[f'{k}_normalized'] for k in ['total_size', 'counter', 'num_page', 'num_img', 'img_ratio', 'size_ratio']]
      weights  = [0.1, 0.5, 0.1, 0.1, 0.1, 0.1]
      tm['score'] = tm['num_img_normalized']*tm['counter_normalized']*sum([w*f for w,f in zip(weights, features)])

    urls_sort = (sorted(temp_modified, key = lambda k: (-k['score'], -k['counter'])))
    length = min(num_final, len(urls_sort))

    stats_file = current_folder.joinpath(f'{current_time} {required_name} - stats report.txt')
    check_file(stats_file)

    out_text = f'F0 keywords     = {", ".join(self.parameters["required"])}\nDeck Attributes = {", ".join(self.parameters["das"])}\n\n'
    for i, url in tqdm(enumerate(urls_sort[:length]), desc='Saving PDF results...', total=length):
      if url['title'] == '' or url['title'] == None:
        file_save = f'{i+1}.pdf'
      else:
        file_save = replace_name(f'{i+1} - {url["title"]}', temp_folder) + '.pdf'
      file_location = temp_folder.joinpath(url['location'])
      _ = file_location.rename(current_folder.joinpath(file_save))
      out_text += f'{i+1}. '
      if url['title'] != None:
        out_text += f'{url["title"]} '
      if url['date'] == '':
        out_text += stats_output(url) + '\n\n'
      else:
        out_text += stats_output(url) + f'Date       : {url["date"]}\n\n'

    with open(stats_file, 'a') as fw:
      fw.write(out_text)
    
    super().printing_error(urls_processing)
    shutil.rmtree(temp_folder)
    return current_folder, stats_file