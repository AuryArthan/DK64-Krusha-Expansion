"""Private rainbow-coin jingle, transposed three semitones; native145 stays exact.

Rare compressed-sequence byte/event layout follows the supplied DK64 decomp
n_csq.c (__getTrackByte/__n_alCSeqTrackEvent). Expand backreferences before editing
notes, retaining every delta, duration, program, controller and tempo.
"""
import struct
from barrel_assets import read_file


def payload(rom, semitones=3):
    source=read_file(rom,0,145);offsets=struct.unpack_from('>16I',source);out=bytearray(68);new_offsets=[];notes=0
    for first in offsets:
        if not first:new_offsets.append(0);continue
        pos=first;backup=remaining=0;stream=bytearray();last=0
        def get():
            nonlocal pos,backup,remaining
            if remaining:
                value=source[backup];backup+=1;remaining-=1;return value
            value=source[pos];pos+=1
            if value==0xfe:
                high=source[pos];pos+=1
                if high!=0xfe:
                    distance=high*256+source[pos];remaining=source[pos+1];pos+=2
                    backup=pos-(distance+4);assert 0<=backup<len(source)and remaining
                    value=source[backup];backup+=1;remaining-=1
            return value
        def byte(value):stream.append(value);stream.extend(b'\xfe'if value==0xfe else b'')
        def varlen():
            for _ in range(5):
                v=get();byte(v)
                if not(v&128):return
            raise AssertionError('Invalid sequence VLQ')
        for _ in range(1000):
            varlen();status=get();byte(status)
            if status==0xff:
                kind=get();byte(kind);last=0
                if kind==0x2f:break
                assert kind in(0x51,0x2e)
                for _ in range(3 if kind==0x51 else 2):byte(get())
            else:
                if status&128:
                    last=status;value=get()
                else:
                    assert last;value=status;stream.pop() # running-status byte is the first data byte
                if last>>4 in(8,9):value+=semitones;notes+=1;assert 0<=value<128
                byte(value)
                if last>>4 not in(0xc,0xd):
                    byte(get())
                    if last>>4==9:varlen()
        else:raise AssertionError('Missing sequence end')
        new_offsets.append(len(out));out.extend(stream)
    struct.pack_into('>16I',out,0,*new_offsets);out[64:68]=source[64:68];assert notes>20
    return bytes(out)
