



'''
fs=open("e:\\adv_super\\html\\f.jpg","rb")
b=fs.read()  #bytes
ft=open("myflower.jpg","wb")
ft.write(b)
fs.close()
ft.close()
print("Image is copied")
'''

with open("e:\\adv_super\\html\\f.jpg","rb") as fs:
    b=fs.read()
    with open("myflower.jpg","wb") as ft:
        ft.write(b)

print("Image is copied ")








