
import threading

class Shashi(threading.Thread):
    def run(self):
        for i in range(1,11):
            print("Shashi .... ",i)

class Sssit(threading.Thread):
    def run(self):
        for i in range(20,31):
            print("Sssit >>> ",i)

''' calling '''
s=Shashi()
st=Sssit()
s.start()
st.start()
