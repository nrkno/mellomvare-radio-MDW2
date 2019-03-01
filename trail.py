"Fjerner trailing ws"

import os
import re
PATH = '/Users/n12327/Documents/Xcode prosjekter/MDW2'

re_strip = re.compile(r'[ \t]+(\n|\Z)')

for path, dirs, files in os.walk(PATH):
    for f in files:
        file_name, file_extension = os.path.splitext(f)
        if file_extension == '.py':
            path_name = os.path.join(path, f)
            with open(path_name, 'r') as fh:
                data = fh.read()

            data = re_strip.sub(r'\1', data)

            with open(path_name, 'w') as fh:
                fh.write(data)

