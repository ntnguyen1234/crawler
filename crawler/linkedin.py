from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import pickle
from selenium.webdriver.common.by import By
from crawler.article import ArticleCrawler
from crawler.pdfcrawler import PDFCrawler
from crawler.generalcrawler import Crawler
from crawler.searcher import Serper
from crawler.utils import *

class LinkedInCrawler(Crawler):
  def __init__(self, searcher: Serper, parameters: dict, scroll: int=20, delay: int=5):
    super().__init__(searcher, parameters)
    if not os.path.exists("data"):
      os.makedirs("data")
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    self.scroll = scroll
    self.delay  = delay
    self.parameters['type'] = 'linkedin'
    self.driver = get_driver()
    logging.info("Starting driver")
    
  def login(self):
    """Go to linkedin and login"""
    # go to linkedin:
    logging.info("Logging in")
    self.driver.maximize_window()
    self.driver.get('https://www.linkedin.com/login')
    time.sleep(self.delay)

    self.driver.find_elements(By.ID, 'username')[0].send_keys(self.parameters['email'])
    self.driver.find_elements(By.ID, 'password')[0].send_keys(self.parameters['password'])
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
    wait_time = self.delay
    reload = 0
    while posts_button == [] and reload < 5:
      wait_time += 1
      reload += 1
      # self.driver.execute_script("location.reload(true);")
      self.close_session()
      self.driver = get_driver()
      self.driver.get(url)
      self.wait(wait_time)
      posts_button = self.driver.find_elements(By.CSS_SELECTOR, 'button[aria-label="Posts"]')
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
    for req in self.parameters['required']:
      for da in self.parameters['das']:
        q = f'"{req}" {da}'
        print(q)
        _ = self.search_linkedin(q, location)
        logging.info('Scrolling...')
        for _ in tqdm(range(self.scroll)):
          self.wait(2)
          self.driver.execute_script('window.scrollBy({top: -window.innerHeight, left: 0, behavior: "smooth"});')
          self.wait(2)
          self.driver.execute_script('window.scrollBy({top: document.body.scrollHeight, left: 0, behavior: "smooth"});')
        posts = self.driver.find_elements(By.CSS_SELECTOR, 'span[dir="ltr"] a[href]')
        
        for post in posts:
          url = post.get_attribute('href')
          if 'linkedin.com' in url or not url.startswith('http'): continue
          urls.append({'url': url, 'date': ''})
        self.close_session()
        self.driver = get_driver()
    self.close_session()
    return urls

  def run(self, PDFCrawl: PDFCrawler, ArticleCrawl: ArticleCrawler, project_name: str='', num_final: int=30, location: str=''):
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
    search_urls = self.crawl()
    self.wait()
    current_folder, temp_folder, urls_processing, required_name = super().process_urls(search_urls, project_name, 'linkedin')
    final = {}
    for ty in ['pdf', 'article']:
      final[ty] = {}
      current_folder.joinpath(ty).mkdir(parents=True, exist_ok=True)
    final['pdf']['current_folder'], final['pdf']['output_file'] = PDFCrawl.save_pdf(current_folder.joinpath('pdf'), temp_folder, urls_processing, required_name, num_final)
    final['article']['current_folder'], final['article']['output_file'] = ArticleCrawl.save_article(current_folder.joinpath('article'), urls_processing, required_name, num_final)
    super().printing_error(urls_processing)
    return current_folder