



import gc

print("GC is enabled ? : ",gc.isenabled())
gc.disable()
print("GC is enabled ? : ",gc.isenabled())

gc.collect()
gc.enable()
print("GC is enabled ? : ",gc.isenabled())
