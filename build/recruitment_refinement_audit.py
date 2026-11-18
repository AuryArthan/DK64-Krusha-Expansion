"""Read-only audit helpers for the colored-key/prison refinement build."""
import struct,zlib,math
from barrel_assets import read_file


def events(data):
    """Independent Rare CSeq reader; compare musical events, not encoding."""
    tracks=[]
    for first in struct.unpack_from('>16I',data):
        if not first:tracks.append([]);continue
        pos=first;back=[];last=0;out=[]
        def get():
            nonlocal pos,back
            if back:return back.pop(0)
            value=data[pos];pos+=1
            if value==254:
                hi=data[pos];pos+=1
                if hi!=254:
                    lo,n=data[pos:pos+2];pos+=2
                    start=pos-(hi*256+lo+4);assert 0<=start<pos and n
                    back=list(data[start:start+n]);return back.pop(0)
            return value
        def vlq():
            value=0
            for _ in range(5):
                v=get();value=value*128+(v&127)
                if v<128:return value
            raise AssertionError('Invalid VLQ')
        for _ in range(1000):
            delta=vlq();status=get()
            if status==255:
                kind=get();last=0;assert kind in(0x51,0x2e,0x2f)
                out.append((delta,255,kind,*[get()for _ in range(3 if kind==0x51 else 2 if kind==0x2e else 0)]))
                if kind==0x2f:break
            else:
                if status&128:last=status;first=get()
                else:first=status;assert last
                row=[delta,last,first]
                if last>>4 not in(12,13):
                    row.append(get())
                    if last>>4==9:row.append(vlq())
                out.append(tuple(row))
        else:raise AssertionError('Missing track end')
        tracks.append(out)
    return tracks


def extra(r,b,clean,path,check,report,sym):
    from recruitment_key_sound import payload
    from recruitment_bridge import triangles,SHIP,PRISON
    from recruitment_spikes import triangles as horns
    from recruitment_collision import LOCAL_DOOR_TANGENT as t,LOCAL_DOOR_NORMAL as n
    original=read_file(clean,0,145);jingle=read_file(r,27,229)
    check('native rainbow coin sequence remains byte-exact',read_file(r,0,145)==original)
    check('private sequence matches generator and native342-byte buffer',jingle==payload(clean)and len(jingle)<=342,len(jingle))
    old,new=events(original),events(jingle);wanted=[];notes=0
    for track in old:
        edited=[]
        for event in track:
            e=list(event)
            if e[1]>>4 in(8,9):e[2]+=3;notes+=1
            edited.append(tuple(e))
        wanted.append(edited)
    check('only note pitches change by3 semitones, all timing/controllers exact',new==wanted and notes>20,notes)
    check('sequence division unchanged',jingle[64:68]==original[64:68])
    points=horns(t,n)
    for i,tip in enumerate((335,282,220)):
        vertices=[p for tri,_ in points[i*24:(i+1)*24]for p in tri]
        peak=max(vertices,key=lambda p:p[1])
        check('horn on sagittal axis and descending '+str(i),abs(peak[0]*t[0]+peak[2]*t[1])<1e-6 and peak[1]==tip,peak)
    tether=triangles(clean)
    check('original tether and anchors supply exactly36 triangles',len(tether)==36 and {v['texture']for v in tether}=={0x50f,0x24e,0x251})
    check('tether anchors join ship and private landing',SHIP==(2832.,500.,3288.)and PRISON==(2925.,498.,3288.))
    check('all tether local vertices are bounded and collide',sum(bool(t.get('bridge'))for t in report['source_triangles'])==36 and report['collision']['walls']==266)
    native=zlib.decompressobj(-15).decompress(r[0x113fa:]);base=0x805fb300
    native_old=zlib.decompressobj(-15).decompress(b[0x113fa:])
    for address,name in ((0x80636bac,'krushamodel2textureidentity'),(0x806368a0,'krushamodel2textureidentity'),(0x8060a324,'krusharecruitmentmusicload')):
        off=address-base;before=struct.unpack_from('>I',native_old,off)[0];after=struct.unpack_from('>I',native,off)[0]
        check('targeted native JAL and unchanged delay slot '+hex(address),before==(0x0c17d225 if address!=0x8060a324 else 0x0c182c50) and after==((0x0c000000|((sym[name]&0xfffffff)>>2)) if address!=0x8060a324 else before) and native[off+4:off+8]==native_old[off+4:off+8],dict(before=hex(before),after=hex(after)))
