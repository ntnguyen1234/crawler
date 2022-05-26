import pathlib
from pathlib import Path
from datetime import date, datetime
import fitz
import sys
import joblib
import contextlib
from tqdm import tqdm

global today, current_time
today = date.today().strftime('%Y%m%d')
current_time = datetime.now().strftime('[%Y%m%d-%H%M]')

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

def set_folder(is_colab: bool, project_name: str, crawl_type: str, required: list):
  if is_colab:
    crawl_folder = Path.cwd().parents[0].joinpath(f'drive/MyDrive/Colab Notebooks/crawl_data/{project_name}')
  else:
    crawl_folder = Path.cwd().joinpath(f'{project_name}')
  crawltype_folder = crawl_folder.joinpath(f'{crawl_type}')
  crawltype_folder.mkdir(parents=True, exist_ok=True)

  required_name = ' - '.join([r.replace('"', '') for r in required])
  required_folder = crawltype_folder.joinpath(f'{current_time} {required_name}')
  required_folder.mkdir(parents=True, exist_ok=True)
  return required_folder, required_name

def readwrite_pdf(content, current_folder: str, i: int, url: dict):
  with fitz.open(stream=content) as doc:
    num_page = doc.page_count
    info = doc.metadata

  if doc.metadata and doc.metadata['creationDate'] != '':
    dt = datetime.strptime(info['creationDate'][:10], 'D:%Y%m%d')
    dt = datetime.strftime(dt, '%b %d, %Y')
  else:
    dt = url['date']

  pdf_info = {
    'url'       : url['url'],
    'counter'   : url['counter'],
    'num_page'  : int(num_page),
    'title'     : info['title'],
    'date'      : dt,
    'num_img'   : 0,
    'total_size': 0,
  }
  
  if pdf_info['title'] == '' or 'title' not in info or info['title'] == '':
    file_save = f'{i+1}'
  else:
    file_save = f'{i+1} - {pdf_info["title"].replace("?"," ").replace(":","-").replace("/","-").replace("|","-")}.pdf'
    file_save = file_save.replace('\\', '-').replace('"', '').replace('\\n', '')
  file_location = current_folder.joinpath(f'{file_save}')
  pdf_info['location'] = file_save

  with open(file_location, 'wb') as fw:
    fw.write(content)
  
  with fitz.open(file_location) as pdf_file:
    for page_index in range(len(pdf_file)):
      page = pdf_file[page_index]
      for img_info, img in zip(page.get_image_info(), page.get_images()):
        if img_info['height'] < 200 or img_info['width'] < 200: continue
        base_image = pdf_file.extract_image(img[0])
        pdf_info['num_img']    += 1
        pdf_info['total_size'] += sys.getsizeof(base_image['image'])
  pdf_info['img_ratio' ] = pdf_info['num_img']/pdf_info['num_page']
  pdf_info['size_ratio'] = pdf_info['total_size']/(pdf_info['num_img'] + 1e-6)
  return pdf_info

def sort_urls(urls):
  seen = set()
  urls_info = []
  for url in urls:
    if url['url'] in seen: continue
    seen.add(url['url'])
    counter = urls.count(url)
    urls_info.append({
      'url'    : url['url'],
      'counter': counter,
      'date'   : url['date'],
    })
  return (sorted(urls_info, key = lambda k: -k['counter']))
  

def stats_output(url_dict):
  return f"""({url_dict["url"]})
  Score      : {url_dict["score"]}
  Img size   : {url_dict["total_size"]}
  Counter    : {url_dict["counter"]}
  Page num   : {url_dict["num_page"]}
  Img num    : {url_dict["num_img"]}
  Img ratio  : {url_dict["img_ratio"]}
  Size ratio : {url_dict["size_ratio"]}
  """

def check_file(output_file):
  if pathlib.Path(output_file).is_file():
    rem_file = pathlib.Path(output_file)
    rem_file.unlink()

def unique(sequence):
  seen = set()
  return [x for x in sequence if not (x in seen or seen.add(x))]

def default_input(default, typ):
  user_input = input('>>> ')
  if user_input == '': return default
  else: return typ(user_input)

def loop_input(command):
  while True:
    print(command)
    user_input = input('>>> ')
    if user_input != '':
      return user_input