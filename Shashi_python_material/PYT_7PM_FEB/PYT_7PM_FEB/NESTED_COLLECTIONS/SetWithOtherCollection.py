

'''
s={
      [10,20,30,40],
      (1.1,2.2,3.3),
      {"aaa","bbb","ccc"},
      {"sno":101,"sname":"roja","scity":"hyd"}
   }
TypeError: unhashable type: 'list'

s={      
      (1.1,2.2,3.3),
      {"aaa","bbb","ccc"},
      {"sno":101,"sname":"roja","scity":"hyd"}
   }
TypeError: unhashable type: 'set'
'''

'''
s={      
      (1.1,2.2,3.3),     
      {"sno":101,"sname":"roja","scity":"hyd"}
   }
TypeError: unhashable type: 'dict'
'''

s={("aaa","bbb","ccc"),(10,20,30),(1.1,2.2,3.3)}

import time
for i in s:
    time.sleep(.2)
    print(i)








