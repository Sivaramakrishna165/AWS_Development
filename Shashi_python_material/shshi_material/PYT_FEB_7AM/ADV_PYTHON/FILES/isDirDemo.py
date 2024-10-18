

import os.path

if os.path.exists("e:\\adv_super\\jdbc"):
    print("Path is Existed ")
    if os.path.isdir("e:\\adv_super\\jdbc"):
        print("Path is a directory")
    else:
        print("Path is not a directory")
else:
    print("Sorry Path is Not Existed ")
