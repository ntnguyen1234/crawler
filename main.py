import json
from crawler import *

def main():
  num_result = 40
  with open(Path.cwd().parents[0].joinpath('parameters.json'), 'r') as fr:
    parameters = json.load(fr)

  project_name = loop_input('\nProject name (i.e. emmay):')

  print('\nWhich type you want to search? \n1. PDF (default) \n2. Article (not available yet) \n3. LinkedIn (not available)')
  search_type = 0
  while search_type not in range(1,4):
    search_type = default_input(1, int)

  required_str = loop_input('\nF0 keywords. Put "," between each keyword (i.e alternative protein):')
  required = required_str.replace(', ',',').split(',')

  das_default = 'market, revenue, valuation, growth, business model, customer, benefit, position, competitor'
  print(f'\nDeck Attributes. Put "," between attribute (i.e market, revenue)\nDefault are "{das_default}":\nPress Enter to leave as default.')
  das_str = default_input(das_default, str)
  das = das_str.replace(', ',',').split(',')

  print('\nNumber of PDF files. Default is 30. Press Enter to leave as default.')
  pdf_num = default_input(30, int)

  GoogleSearcher = Serper('google')
  GoogleSearcher.api_key = parameters['api_key']
  is_colab = parameters['is_colab']
  PDFCrawl = PDFCrawler(GoogleSearcher, required, das, is_colab)

  if search_type == 1:
    current_folder, stats_file = PDFCrawl.pdf_collect(project_name, num_result, pdf_num)
  elif search_type == 3:
    LinkedinCrawl  = LinkedInCrawler(
      searcher = GoogleSearcher,
      required = required, 
      das      = das, 
      is_colab = is_colab, 
      scroll   = 20,
      delay    = 5, 
      email    = parameters['linkedin_mail'], 
      password = parameters['linkedin_pass'],
    )
    current_folder, stats_file = LinkedinCrawl.run(PDFCrawl, project_name, pdf_num)
  print(current_folder)
  print(stats_file)
  # if is_colab:
  #   print(f'\nResults are in folder: {str(current_folder).split("MyDrive")[1]}')
  #   print(f'Stats report is in folder: {str(stats_file).split("MyDrive")[1]}')

if __name__ == '__main__':
  main()