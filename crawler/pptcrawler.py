from crawler.generalcrawler import Crawler
from crawler.converter import Converter
from crawler.searcher import Serper
from crawler.utils import *

class PPTCrawler(Crawler):
  def __init__(self, searcher: Serper, parameters: dict, types: dict={'crawl_type': 'ppt', 'ppt_api': 'aspose'}):
    super().__init__(searcher, parameters)
    self.types = types
    self.converter  = Converter(self.parameters)

  def ppt_collect(self, project_name: str, num_result: int=40, num_final: int=30):
    search_urls = super().search(' filetype:pptx', num_result)
    search_urls.extend(super().search(' filetype:ppt', num_result))
    current_folder, temp_folder, urls_processing, required_name = super().process_urls(search_urls, project_name, self.types)
    print('\n\nConverting ppt to pptx...\n\n')
    _ = self.converter.convert_libre(temp_folder, 'pptx')
    waitfor_process(['soffice'])

    manager = Manager()
    urls_ppt = {
      'ppt'  : manager.list(),
      'error': manager.list(),
    }
    with tqdm_joblib(tqdm(desc='Getting PPT info...', total=len(urls_processing['ppt']))) as _:
      Parallel(n_jobs=-1, verbose=0)(delayed(self.converter.process_ppt)(urls_ppt, url) for url in urls_processing['ppt'])
    urls_ppt['error'] = urls_processing['error']
    return self.save_ppt(current_folder, temp_folder, urls_ppt, required_name, num_final)

  def saveto_pdf(self, current_folder, out_stats, i: int, url: dict):
    _ = url['location'].rename(current_folder / f'{i+1} - {url["title"]}.pptx')
    stat = {'index': i+1}
    stat['content'] = f'{i+1}. '
    if url['title'] != None:
      stat['content'] += f'{url["title"]} '
    if url['date'] == '':
      stat['content'] += stats_output(url) + '\n\n'
    else:
      stat['content'] += stats_output(url) + f'Date       : {url["date"]}\n\n'
    out_stats.append(stat)

  def save_ppt(self, current_folder, temp_folder, urls_processing: dict, required_name: str, num_final: int=30):
    temp_modified = [{f'{k}_normalized': t[k]/(max([te[k] for te in urls_processing['ppt']]) + 1e-6) for k in t.keys() if k not in ['url', 'title', 'date', 'location']} for t in urls_processing['ppt']]
    for tm, te in zip(temp_modified, urls_processing['ppt']):
      for k in te.keys():
        tm[k] = te[k]
      if len(self.parameters['das']) > 1:
        features = [tm[f'{k}_normalized'] for k in ['counter', 'keywords', 'num_page', 'num_img', 'img_ratio']]
        weights  = [0.6, 0.1, 0.1, 0.1, 0.1]
        tm['score'] = tm['num_img_normalized']*tm['keywords_normalized']*tm['counter_normalized']*sum([w*f for w,f in zip(weights, features)])
      else:
        features = [tm[f'{k}_normalized'] for k in ['keywords', 'num_page', 'num_img', 'img_ratio']]
        weights  = [0.1, 0.1, 0.7, 0.1]
        tm['score'] = tm['num_img_normalized']*tm['keywords_normalized']*sum([w*f for w,f in zip(weights, features)])

    urls_sort = (sorted(temp_modified, key = lambda k: (-k['score'], -k['counter'])))
    length = min(num_final, len(urls_sort))

    stats_file = current_folder.joinpath(f'{current_time} {required_name} - stats report.txt')
    check_file(stats_file)

    out_text = f'F0 keywords     = {", ".join(self.parameters["required"])}\nDeck Attributes = {", ".join(self.parameters["das"])}\n\n'
    manager = Manager()
    out_stats = manager.list()
    length = min(len(urls_sort), num_final)
    with tqdm_joblib(tqdm(desc='Saving PPT results...', total=length)) as _:
      Parallel(n_jobs=-1, verbose=0)(delayed(self.saveto_pdf)(current_folder, out_stats, i, url) for i, url in enumerate(urls_sort[:length]))
    
    print('\n\nConverting pptx to pdf...\n\n')
    _ = self.converter.convert_libre(current_folder, 'pdf')
    waitfor_process(['soffice'])
    for file in current_folder.glob('**/*.pptx'):
      file.unlink()
    shutil.rmtree(temp_folder)
    out_stats = (sorted(out_stats, key = lambda k: k['index']))
    out_text += ''.join([stat['content'] for stat in out_stats])

    with open(stats_file, 'a') as fw:
      fw.write(out_text)
    
    super().printing_error(urls_processing)
    return current_folder, stats_file