import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from bs4 import BeautifulSoup
import logging
import pickle
import os
import selenium
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
from crawler.pdfcrawler import PDFCrawler
from crawler.generalcrawler import Crawler
from crawler.searcher import Serper
from crawler.utils import *

class LinkedInCrawler(Crawler):
  def __init__(self, searcher: Serper, required: list, das: list, is_colab: bool, scroll: int=20, delay: int=5, email: str="", password: str=""):
    super().__init__(searcher, required, das, is_colab)
    if not os.path.exists("data"):
      os.makedirs("data")
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    self.scroll = scroll
    self.delay = delay
    self.email = email
    self.password = password
    self.params = {
      'type' : 'linkedin',
    }
    logging.info("Starting driver")
    options = Options()
    # options.add_argument("--headless")
    # options.add_argument('user_agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0')

    options.add_argument("-profile")
    options.add_argument("C:\\Users\\Administrator\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\r1uc2bce.default")
    self.driver = webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)

  def login(self, email, password):
    """Go to linkedin and login"""
    # go to linkedin:
    logging.info("Logging in")
    self.driver.maximize_window()
    self.driver.get('https://www.linkedin.com/login')
    time.sleep(self.delay)

    self.driver.find_elements(By.ID, 'username')[0].send_keys(email)
    self.driver.find_elements(By.ID, 'password')[0].send_keys(password)
    self.driver.find_elements(By.ID, 'password')[0].send_keys(Keys.RETURN)
    time.sleep(self.delay)

  def save_cookie(self, path):
    with open(path, 'wb') as filehandler:
      pickle.dump(self.driver.get_cookies(), filehandler)

  def load_cookie(self, path):
    with open(path, 'rb') as cookiesfile:
      cookies = pickle.load(cookiesfile)
      for cookie in cookies:
        self.driver.add_cookie(cookie)

  def search_linkedin(self, keywords, location):
    """Enter keywords into search bar
    """
    logging.info("Searching links")
    # query = '+'.join(keywords.split())
    url = f'https://www.linkedin.com/search/results/content/?keywords={keywords}'
    self.driver.get(url)
    self.wait()
    posts_button = self.driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Posts"]')
    wait_time = 5
    reload = 0
    while posts_button == [] and reload < 5:
      wait_time += 1
      reload += 1
      self.driver.execute_script("location.reload(True);")
      self.wait(wait_time)
      print(posts_button)
    # search based on keywords and location and hit enter
    return self.wait_for_element_ready(By.CSS_SELECTOR, 'button[aria-label="Posts"]')
    # time.sleep(self.delay)
    # search_bars = self.driver.find_elements_by_class_name('jobs-search-box__text-input')
    # search_keywords = search_bars[0]
    # search_keywords.send_keys(keywords)
    # search_location = search_bars[2]
    # search_location.send_keys(location)
    # time.sleep(self.delay)
    # search_location.send_keys(Keys.RETURN)
    # logging.info("Keyword search successful")
    # time.sleep(self.delay)

  def wait(self, t_delay=None):
    """Just easier to build this in here.
    Parameters
    ----------
    t_delay [optional] : int
        seconds to wait.
    """
    delay = self.delay if t_delay == None else t_delay
    time.sleep(delay)

  def scroll_to(self, job_list_item):
    """Just a function that will scroll to the list item in the column 
    """
    self.driver.execute_script("arguments[0].scrollIntoView();", job_list_item)
    job_list_item.click()
    time.sleep(self.delay)

  def get_position_data(self, job):
    """Gets the position data for a posting.

    Parameters
    ----------
    job : Selenium webelement

    Returns
    -------
    list of strings : [position, company, location, details]
    """
    [position, company, location] = job.text.split('\n')[:3]
    details = self.driver.find_element_by_id("job-details").text
    return [position, company, location, details]

  def wait_for_element_ready(self, by, text):
    try:
      return WebDriverWait(self.driver, self.delay).until(EC.presence_of_element_located((by, text)))
    except TimeoutException:
      logging.debug("wait_for_element_ready TimeoutException")
      pass

  def close_session(self):
    """This function closes the actual session"""
    logging.info("Closing session")
    self.driver.close()

  def crawl(self, location: str=''):
    logging.info("Begin linkedin keyword search")
    urls = []
    for req in self.required:
      for da in self.das:
        q = f'{req} {da} pdf'
        _ = self.search_linkedin(q, location)
        logging.info('Scrolling...')
        for _ in tqdm(range(20)):
          self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
          self.wait(1)
        posts = self.driver.find_elements(By.CSS_SELECTOR, 'span[dir="ltr"] a[href]')
        
        for post in posts:
          url = post.get_attribute('href')
          if 'linkedin.com' in url or not url.startswith('http'): continue
          urls.append({'url': url, 'date': ''})
    return urls

  def run(self, PDFCrawl: PDFCrawler, project_name: str='', pdf_num: int=30, location: str='', email: str='', password: str=''):
    # if os.path.exists("data/cookies.txt"):
    #   self.driver.get("https://www.linkedin.com/")
    #   self.load_cookie("data/cookies.txt")
    #   self.driver.get("https://www.linkedin.com/")
    # else:
    #   self.login(
    #     email=email,
    #     password=password
    #   )
    #   self.save_cookie("data/cookies.txt")
    urls = self.crawl()
    self.close_session()
    required_folder, urls_sort, required_name = super().collect(urls, project_name, self.params['type'])
    return PDFCrawl.save_pdf(required_folder, urls_sort, required_name, pdf_num)
    