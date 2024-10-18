





fs=open("e:\\adv_super\\html\\f.jpg","rb")
b=fs.read()
ft=open("e:\\2022\\PYT_FEB_7AM\\ADV_PYTHON\\PICKLE\myf.jpg","wb")
ft.write(b)
fs.close()
ft.close()
print("Image is Copied")
        
