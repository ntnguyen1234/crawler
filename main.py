from crawler import *
import json

def main():
  num_result = 40
  with open(Path.cwd().parents[0].joinpath('parameters.json'), 'r') as fr:
    parameters = json.load(fr)

  project_name = loop_input('Project name (i.e. emmay):')
  print('\n')

  required_str = loop_input('F0 keywords. Put "," between each keyword (i.e alternative protein):')
  required = required_str.replace(', ',',').split(',')
  print('\n')

  # das_str = loop_input('Deck Attributes. Put "," between attribute (i.e market, revenue):')
  # das = das_str.replace(', ',',').split(',')
  # print('\n')

  das_default = 'market, revenue, valuation, growth, business model, customer, benefit, position, competitor'
  print(f'Deck Attributes. Put "," between attribute (i.e market, revenue)\nDefault are "{das_default}":\nPress Enter to leave as default.')
  das_str = default_input(das_default, str)
  das = das_str.replace(', ',',').split(',')
  print('\n')

  print('Number of PDF files. Default is 30. Press Enter to leave as default.')
  pdf_num = default_input(30, int)
  print('\n')

  GoogleSearcher = Serper('google')
  GoogleSearcher.api_key = parameters['api_key']
  is_colab = parameters['is_colab']
  PDFCrawling    = PDFCrawler(GoogleSearcher, required, das, is_colab)

  current_folder, stats_file = PDFCrawling.pdf_collect(project_name, num_result, pdf_num)
  if is_colab:
    print(f'\n\nResults are in folder: {str(current_folder).split("MyDrive")[1]}')
    print(f'\n\nStats report is in folder: {str(stats_file).split("MyDrive")[1]}')

if __name__ == '__main__':
  main()