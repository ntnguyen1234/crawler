from crawler import *

def main():
  with open(Path.cwd().parents[0].joinpath('parameters.json'), 'r') as fr:
    parameters = json.load(fr)
  nltk.download('punkt')
  num_result = 40
  os.environ['GH_TOKEN'] = parameters['GH_TOKEN']

  project_name = loop_input('\nProject name (i.e. emmay):')

  print('\nWhich type you want to search? Choose number \n1. PDF (default) \n2. Article \n3. LinkedIn (not available)\nPress Enter to leave as default.')
  search_type = 0
  while search_type not in range(1,4):
    search_type = default_input(1, int)

  required_str = loop_input('\nF0 keywords. Put "," between each keyword (i.e alternative protein):')
  parameters['required'] = required_str.replace(', ',',').split(',')

  das_default = 'market, revenue, valuation, growth, business model, customer, benefit, position, competitor'
  print(f'\nDeck Attributes. Put "," between attribute (i.e market, revenue)\nDefault are "{das_default}":\nPress Enter to leave as default.')
  das_str = default_input(das_default, str)
  parameters['das'] = das_str.replace(', ',',').split(',')

  print('\nNumber of final files. Default is 30. Press Enter to leave as default.')
  num_final = default_input(30, int)

  GoogleSearcher = Serper('google')
  GoogleSearcher.api_key = parameters['api_key']
  PDFCrawl     = PDFCrawler(GoogleSearcher, parameters)
  ArticleCrawl = ArticleCrawler(GoogleSearcher, parameters)

  if search_type == 1:
    current_folder, stats_file = PDFCrawl.pdf_collect(project_name, num_result, num_final)
  elif search_type == 2:
    current_folder, stats_file = ArticleCrawl.article_collect(project_name, num_result, num_final)
  elif search_type == 3:
    LinkedinCrawl  = LinkedInCrawler(GoogleSearcher, parameters)
    current_folder = LinkedinCrawl.run(PDFCrawl, ArticleCrawl, project_name, num_final)
  if parameters['is_colab']:
    print(f'\nResults are in folder    : {str(current_folder).split("MyDrive")[1]}')
    print(f'Stats report is in folder: {str(stats_file).split("MyDrive")[1]}')

if __name__ == '__main__':
  main()