import pathlib
from pathlib import Path
from datetime import date, datetime
import fitz
import sys
import joblib
import contextlib
from tqdm import tqdm
from joblib import Parallel, delayed
import nltk
from readabilipy import simple_json_from_html_string
import bs4
from bs4 import BeautifulSoup
import string
from itertools import groupby
import shutil
import traceback
import selenium
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
import time
import json
from multiprocessing import Manager
import os
from urllib.parse import urlencode, urlparse, parse_qs

global today, current_time, special_domains
today = date.today().strftime('%Y%m%d')
current_time = datetime.now().strftime('[%Y%m%d-%H%M]')
special_domains = [
  # 'crunchbase.com',
  # 'facebook.com',
  # 'instagram.com',
  # 'linkedin.com',
]

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
    file_save = f'{i+1}. {replace_name(pdf_info["title"], current_folder)}'
  file_location = current_folder.joinpath(f'{file_save}.pdf')
  pdf_info['location'] = file_location

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

def readwrite_article(url: dict, details: dict, content_text=None):
  if content_text == None:
    content_text = url['content_text']
  if type(content_text) == bytes:
    content_text = content_text.decode('UTF-8')

  article = simple_json_from_html_string(content_text, use_readability=True)
  if article['title'] == None: return

  # Title
  title = article['title']

  # Raw content
  content_raw = BeautifulSoup(article['plain_content'], features='lxml')

  # Extract text file
  ps = unique(content_raw.select('p, h1, h2, h3'))

  # List of all sentences
  sentences = []
  full_text = ''
  for p in ps:
    for p_content in p.contents:
      if isinstance(p_content, bs4.element.Tag):
        full_text += p_content.text + '\n'
        # Extract sentences
        for token in nltk.sent_tokenize(p_content.text):
          sentences.append(token)
      else:
        full_text += p_content + '\n'
        for token in nltk.sent_tokenize(p_content):
          sentences.append(token)

  # Index of sentences that contain keywords
  tokenizer = nltk.TweetTokenizer()
  article_length = 0
  keywords_count = 0
  indices = []
  for i, sentence in enumerate(sentences):
    article_length += len([x for x in tokenizer.tokenize(sentence) if x not in string.punctuation])
    if any([key.lower() in sentence.lower() for key in details['keywords']]): # Lower case all the words
      keywords_count += sum([sentence.lower().count(key.lower()) for key in details['keywords']])
      for j in range(max(0, i-details['fb']), min(i+details['fb']+1, len(sentences))): # Forward/backward
        indices.append(j)

  # Handle if sentences contain keywords or not
  if len(indices) == 0: return
  elif len(indices) == 1:
    consecutive_indices = [indices]
  else:
    # Split consecutive sentences
    indices_set = list(set(indices))
    gb = groupby(enumerate(indices_set), key=lambda x: x[0] - x[1])
    all_groups = ([i[1] for i in g] for _, g in gb)
    consecutive_indices = list(filter(lambda x: len(x) > 1, all_groups))
  
  # Dictionary of results
  output_dict = {
    'url'    : url['url'],
    'counter': url['counter'],
    'title'  : title,
    'date'   : url['date']
  }
  # Counter for numbers in an article
  num_count = 0
  # Text results
  output_text = []

  for c_index in consecutive_indices:
    # Index of consecutive sentences
    sentence_list = [' '.join(sentences[i].replace('\n', ' ').split()) for i in c_index]
    final_sentences = f'  + {" ".join(sentence_list)}\n'
    output_text.append(final_sentences)

    # Count numbers in article
    # all_tokens = [word_tokenize(t) for t in sent_tokenize(final_sentences)]
    all_tokens = [x for x in tokenizer.tokenize(final_sentences) if x not in string.punctuation]
    for token in all_tokens:
      if token.lstrip('-').replace('.','',1).replace(',','',1).replace('%','',1).replace('$','',1).replace('#','',1).isnumeric():
        num_count += 1
  output_dict['content']      = output_text
  output_dict['num_count']    = num_count
  output_dict['keywords']     = keywords_count
  output_dict['length']       = article_length
  output_dict['full_text']    = full_text
  output_dict['full_content'] = article['content']
  return output_dict

def sort_urls(urls):
  seen = set()
  urls_info = []
  urls_link = [url['url'] for url in urls]
  for url in urls:
    if url['url'] in seen: continue
    seen.add(url['url'])
    if 'counter' in url.keys():
      url['counter'] = url['counter'] + sum([u['counter'] for u in urls if u['url'] == url['url']])
    else:
      url['counter'] = urls_link.count(url['url'])
    urls_info.append(url)
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

def replace_name(name: str, parent_folder) -> str:
  length = 250 - len(str(parent_folder))
  return name[:length].replace('?','').replace(':','-').replace('/','-').replace('|','-').replace('\\','-').replace('"','').replace('\n','').replace('.','-')

def remove_trackings(url):
  u = urlparse(url)
  query = parse_qs(u.query, keep_blank_values=True)
  query_keys = list(query.keys())
  for q in query_keys:
    if q.startswith('utm_'):
      query.pop(q, None)
  return u._replace(query=urlencode(query, True)).geturl()

def get_driver():
  options = Options()
  # options.add_argument("--headless")
  # options.add_argument('user_agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0')

  options.add_argument("-profile")
  options.add_argument("C:\\Users\\Administrator\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\r1uc2bce.default")
  return webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)
  # self.driver = webdriver.Firefox(options=options)