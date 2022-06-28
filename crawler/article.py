from crawler.generalcrawler import Crawler
from crawler.searcher import Serper
from crawler.utils import *
try:
  import pdfkit
except Exception:
  pass

class ArticleCrawler(Crawler):
  def __init__(self, searcher: Serper, parameters: dict):
    super().__init__(searcher, parameters)
    self.details = {
      'keywords': self.parameters['das'],
      'fb'      : 1,
    }

  def article_collect(self, project_name: str, num_result: int=40, num_final: int=30):
    search_urls = super().search(num_result=num_result)
    current_folder, _, urls_processing, required_name = super().process_urls(search_urls, project_name)
    return self.save_article(current_folder, urls_processing, required_name, num_final)

  def save_output(self, current_folder, out_list, i: int, url: dict):
    file_name = f'{i+1}. {replace_name(url["title"], current_folder)}'
    try:
      options = {
        'encoding'        : 'UTF-8',
        'user-style-sheet': 'fonts/merriweather.css'
      }
      article_location = current_folder.joinpath(file_name + '.pdf')
      _ = pdfkit.from_string(f'<p><a href={url["url"]}>{url["url"]}</a></p>' + url['full_content'], article_location, options=options)
    except Exception:
      article_location = current_folder.joinpath(file_name + '.txt')
      with open(article_location, 'w') as fw:
        fw.write(url['full_text'])
      print(f'\n\npdfkit ==========================================\n\n{url["url"]}\n{file_name + ".txt"}\n\n')
      print(traceback.format_exc())
      print('========================================================\n')
    out_text = f'{i+1}. {url["title"]} ({url["url"]}):\n'
    out_text += f'Keywords = {url["keywords"]}\nNumbers  = {url["num_count"]}\nLength   = {url["length"]}\n'
    for c in url['content']:
      out_text += c
    out_text += '\n'
    out_list.append({
      'index': i + 1,
      'text' : out_text,
    })

  def save_article(self, current_folder, urls_processing: dict, required_name: str, num_final: int=30):
    for url in tqdm(urls_processing['raw'], desc='Processing raw documents...', total=len(urls_processing['raw'])):
      try:
        article_info = readwrite_article(url, self.details)
        if article_info != None:
          urls_processing['doc'].append(article_info)
      except Exception:
        urls_processing['error'].append(url)
        print(f'\n\nget_info ==========================================\n\n{url["url"]}\n\n')
        print(traceback.format_exc())
        print('========================================================\n')
    success_list = []
    error_length = len(urls_processing['error'])
    if error_length > 0:
      for url in tqdm(urls_processing['error'], desc='Processing error pages...', total=error_length):
        try:
          content_text = super().scrapingbee(url['url'])
          article_info = readwrite_article(url, self.details, content_text)
          if article_info != None:
            urls_processing['doc'].append(article_info)
            success_list.append(url)
        except Exception:
          print(f'\n\nfallback ==========================================\n\n{url["url"]}\n\n')
          print(traceback.format_exc())
          print('========================================================\n')
      for url in success_list:
        urls_processing['error'].remove(url)

    urls_sort = (sorted(urls_processing['doc'], key = lambda k: (-k['keywords'], -k['num_count'], -k['length'])))

    # Output file
    out_text = f'F0 keywords     = {", ".join(self.parameters["required"])}\nDeck Attributes = {", ".join(self.parameters["das"])}\n\n'
    manager = Manager()
    out_list = manager.list()

    length = min(num_final, len(urls_sort))
    with tqdm_joblib(tqdm(desc='Saving article results...', total=length)) as _:
      Parallel(n_jobs=-1, verbose=0)(delayed(self.save_output)(current_folder, out_list, i, url) for i, url in enumerate(urls_sort[:length]))

    out_list = (sorted(list(out_list), key = lambda k: k['index']))
    for out_l in out_list:
      out_text += out_l['text']

    output_file = current_folder.joinpath(f'{current_time} {required_name}.txt')
    check_file(output_file)

    with open(output_file, 'w') as fw:
      fw.write(out_text)

    super().printing_error(urls_processing)
    return current_folder, output_file