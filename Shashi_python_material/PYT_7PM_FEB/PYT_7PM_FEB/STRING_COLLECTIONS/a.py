
s="welcome"

#S.index(sub[,start,end]) -> int 
#s.index("e").upper() //invalid

'''
print( s[0:3].upper().strip() )
           "wel".upper()
                   "WEL".strip()
                         WEL   '''

print( s.upper().strip().index("E") )

print( "wel" in s.strip().upper() )

                         
