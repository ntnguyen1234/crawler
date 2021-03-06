from crawler import *
from crawler.pptcrawler import PPTCrawler

def main():
  with open(Path.cwd().parents[0].joinpath('parameters.json'), 'r') as fr:
    parameters = json.load(fr)
  nltk.download('punkt', quiet=True)
  os.environ['GH_TOKEN'] = parameters['GH_TOKEN']

  project_name = loop_input('\nProject name (i.e. emmay):')

  print('\nWhich type you want to search? Choose number \n1. PDF (default) \n2. Article (not available) \n3. Powerpoint (not available) \n4. LinkedIn (not available)\nPress Enter to leave as default.')
  search_type = 0
  while search_type not in range(1,5):
    search_type = default_input(1, int)

  required_str = loop_input('\nF0 keywords. Put "," between each keyword (i.e alternative protein):')
  parameters['required'] = required_str.replace(', ',',').split(',')

  das_default = 'market, revenue, valuation, growth, business model, customer, benefit, positioning, competitor'
  print(f'\nDeck Attributes. Put "," between each attribute (i.e market, revenue)\nExamples are "{das_default}":')
  das_str = input('>>> ')

  print('\nNumber of results in each search. Default is 40. Press Enter to leave as default.')
  num_result = default_input(40, int)

  print('\nNumber of final files. Default is 100. Press Enter to leave as default.')
  num_final = default_input(100, int)

  if len(das_str.split()) == 0 and len(das_str.split(',')) == 0:
    parameters['das'] = ['']
  else:
    parameters['das'] = das_str.replace(', ',',').split(',')

  GoogleSearcher = Serper('google', parameters)
  _ = GoogleSearcher.get_total_searches()
  # print(f'\nThere are {total_searches} searches left\n')

  # max_searches   = len(parameters['required']) * len(parameters['das']) * (int((num_result - 10)/20) + 2)
  # if search_type == 3: max_searches *= 2
  # if total_searches < max_searches:
  #   print(f'\nWarning! You might lack {max_searches - total_searches} API searches. Please add or renew another API.')

  required_filter = required_str.replace('"', '')
  print(f'\nKeywords to filter. Default is "{required_filter}".\nPut "," between each filter keyword.\nPut ";" between each list of the same type of filter keywords. ')
  filter_str = input('>>> ')
  if filter_str:
    # parameters['filters'] = filter_str.replace(', ',',').split(',')
    parameters['filters'] = [f_str.replace(', ', ',').split(',') for f_str in filter_str.replace('; ', ';').split(';')]
  else:
    parameters['filters'] = [parameters['required']]

  print('')
  PDFCrawl     = PDFCrawler(GoogleSearcher, parameters)
  PPTCrawl     = PPTCrawler(GoogleSearcher, parameters)
  ArticleCrawl = ArticleCrawler(GoogleSearcher, parameters)

  if search_type == 1:
    current_folder, stats_file = PDFCrawl.pdf_collect(project_name, num_result, num_final)
  elif search_type == 2:
    current_folder, stats_file = ArticleCrawl.article_collect(project_name, num_result, num_final)
  elif search_type == 3:
    current_folder, stats_file = PPTCrawl.ppt_collect(project_name, num_result, num_final)
  elif search_type == 4:
    LinkedinCrawl  = LinkedInCrawler(GoogleSearcher, parameters)
    current_folder = LinkedinCrawl.run(PDFCrawl, ArticleCrawl, project_name, num_final)

  if parameters['is_colab']:
    print(f'\nResults are in folder    : {str(current_folder).split("MyDrive")[1]}')
    print(f'Stats report is in folder: {str(stats_file).split("MyDrive")[1]}')

if __name__ == '__main__':
  main()