


import os.path

if os.path.exists("e:\\adv_super\\html"):
    print("Path is Existed ")

    if os.path.isdir("e:\\adv_super\\html"):
        print("Yes it is a directory ")
    else:
        print("Sorry Path is not directory")
        
else:
    print("Sorry Path Not Existed ")
