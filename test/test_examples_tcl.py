from pyvmd_movies import *

import os

examples = ['../examples/' + x for x in os.listdir('../examples') if os.path.isdir('../examples/' + x)]

for ex in examples:
    txt_files = [x for x in os.listdir(ex) if x.endswith('txt')]
    for script in txt_files:
        script_file = ex + '/' + script
        print("Testing {}  ...".format(script_file))
        scr = Script(script_file)
        for scene in scr.scenes:
            _ = scene.tcl()

print("\n\n\n\t\tSuccess - all input files parsed without errors!\n\n\n")