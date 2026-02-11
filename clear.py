import os
import shutil


def clear_file(directory, del_name=['__pycache__']):
    for root, dirs, files in os.walk(directory):
        for n in del_name:
            if n in dirs:
                cache_path = os.path.join(root, n)
                shutil.rmtree(cache_path)
                print(f"delete {cache_path}")
            if n in files:
                cache_path = os.path.join(root, n)
                os.remove(cache_path)
                print(f"delete {cache_path}")


clear_file(os.getcwd(), ['__pycache__', '.DS_Store'])
