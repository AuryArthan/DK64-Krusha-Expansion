"""Native row/carousel option inputs shared by current and historical QA tools."""
def compact(symbols):return 'gameoptionsmode' in symbols

def tap(d,key):
    d.cmd(down=[key],wait=0)
    try:d.wait_frames(3,timeout=90)
    finally:d.cmd(up=[key],wait=0)
    d.wait_frames(4,timeout=90)

def global_flag(d,flag):
    bits=(((d.mem(0x807ECEA0,'u16')+0x6B7)&~63)+0x27)&~7
    base=0x807ECEA8+((bits*4+63)&~63)//8
    return (d.mem(base+flag//8,'u8')>>(flag%8))&1

def value(d,index,enabled_address):
    if index==0:return d.mem(0x807444C0,'u8')
    if index==1:return 2 if d.mem(0x8074452C,'u8') else global_flag(d,0x2C)
    if index==4:return d.mem(enabled_address)
    if index==5:return global_flag(d,0x2D)
    raise ValueError(index)

def select(d,data,index,symbols,ready):
    for _ in range(12):
        assert ready(9)
        if d.mem(data+0x17,'u8')==index:return
        tap(d,'Down' if compact(symbols) else 'Right')
    raise RuntimeError('Options row not selected')

def set_value(d,data,index,wanted,symbols,enabled_address,ready):
    select(d,data,index,symbols,ready)
    for _ in range(3):
        if value(d,index,enabled_address)==wanted:return
        tap(d,'Right' if compact(symbols) else 'Up');assert ready(9)
    assert value(d,index,enabled_address)==wanted,('Option mismatch',index,wanted)
