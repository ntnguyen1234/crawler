import pathlib
from pathlib import Path
from datetime import date

global today
today = date.today().strftime('%Y%m%d')

def create_folder(parent_dir):
  folder_list = [dir.parts[-1] for dir in parent_dir.iterdir() if dir.is_dir()]
  if len(folder_list) == 0:
    return parent_dir.joinpath(f'{len(folder_list)+1}')  
  max_number = max([int(dir) for dir in folder_list if dir.isnumeric()])
  for i in range(1, max_number+1):
    temp_dir = parent_dir.joinpath(str(i))
    if not temp_dir.is_dir() or next(Path(temp_dir).iterdir(), None) == None:
      return temp_dir
  return parent_dir.joinpath(f'{len(folder_list)+1}')

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