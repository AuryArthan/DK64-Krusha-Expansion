'use strict';
(() => {
const $=id=>document.getElementById(id);
const colors={DK:'#e2bb18',Diddy:'#dd4c3e',Lanky:'#448bdd',Tiny:'#aa5ac8',Chunky:'#56a64f',Shared:'#f2f0df',Unknown:'#7c8583',Krusha:'#d0d0d0'};
const kinds={single:['Single banana','●'],bunch:['Banana bunch ×5','◆'],balloon:['Balloon ×10 (anchor)','○'],coin:['Colored coin','○'],gb:['Golden Banana','★'],blueprint:['Kasplat / blueprint','■'],medal:['Helm medal','⬟'],fairy:['Fairy (anchor)','✧'],rainbow:['Rainbow coin / dirt patch','⊕'],crown:['Crown / pad','♛'],quest:['Key / company coin / bean / pearl','⬟'],bonus:['Bonus barrel (reward site)','B'],supply:['Shared supplies','+'],landmark:['Shops / warps / tag barrels / boss portals','T'],exit:['Area entrance / exit','↗']};
const canvas=$('map'),ctx=canvas.getContext('2d'),catalog=window.ATLAS_CATALOG.maps;
let map=null,style='A',zoom=1,pan=[0,0],bounds=null,view=null,hit=[],request=0,selected=null,drag=null,planner=null,yaw=45,cosYaw=Math.SQRT1_2,sinYaw=Math.SQRT1_2,terrainCache=null;
const filteredOwners=new Set(Object.keys(colors));
const filteredKinds=new Set(Object.keys(kinds).filter(k=>!['supply','landmark','exit'].includes(k)));
const params=new URLSearchParams(location.search);
if(params.get('style')==='C')style='C';
if(params.has('yaw')&&Number.isFinite(Number(params.get('yaw'))))yaw=((Number(params.get('yaw'))%360)+360)%360;
cosYaw=Math.cos(yaw*Math.PI/180);sinYaw=Math.sin(yaw*Math.PI/180);
function owner(p){return p.owner||(p.kind==='gb'||p.kind==='bonus'?'Unknown':'Shared');}
function checkboxes(target,entries,enabled,onchange){
 for(const [key,label] of entries){const l=document.createElement('label');l.className='check';const c=document.createElement('input');c.type='checkbox';c.checked=enabled.has(key);c.addEventListener('change',()=>{c.checked?enabled.add(key):enabled.delete(key);onchange();});l.append(c);
 if(target==='owners'){const s=document.createElement('span');s.className='swatch';s.style.background=colors[key];l.append(s);}
 l.append(document.createTextNode(label));$(target).append(l);}
}
checkboxes('owners',Object.keys(colors).map(k=>[k,k==='Shared'?'Shared / no character ownership':k==='Unknown'?'Reward owner not resolved':k==='Krusha'?'Krusha proposals':k]),filteredOwners,refresh);
checkboxes('kinds',Object.entries(kinds).map(([k,v])=>[k,v[0]]),filteredKinds,refresh);
function nav(){
 const q=$('search').value.toLowerCase(),parent=$('maps');parent.replaceChildren();
 const groups=['DK Isles','Jungle Japes','Angry Aztec','Frantic Factory','Gloomy Galleon','Fungi Forest','Crystal Caves','Creepy Castle','Hideout Helm','Shared interiors','Other maps / bonus games'];
 for(const g of groups){const matches=catalog.filter(m=>m.group===g&&m.name.toLowerCase().includes(q));if(!matches.length)continue;
 const d=document.createElement('details');d.open=!!q||g===map?.meta.group;const s=document.createElement('summary');s.textContent=g+' · '+matches.length;d.append(s);
 for(const m of matches){const b=document.createElement('button');b.textContent=m.name;b.title=`Map ${m.id} · ${m.points} reference markers`;if(map?.meta.id===m.id)b.className='active';b.onclick=()=>load(m.id);d.append(b);}parent.append(d);}
}
function height(){return [Number($('miny').value),Number($('maxy').value)];}
function visible(){if(!map)return [];const [lo,hi]=height();return map.points.filter(p=>filteredKinds.has(p.kind)&&filteredOwners.has(owner(p))&&p.xyz[1]>=lo&&p.xyz[1]<=hi);}
function project(p){return style==='C'?[p[0]*cosYaw-p[2]*sinYaw,(p[0]*sinYaw+p[2]*cosYaw)*.5-p[1]*.70]:[p[0],p[2]];}
function up(t){return (t[5]-t[2])*(t[6]-t[0])-(t[3]-t[0])*(t[8]-t[2])>0;}
function validfloor(t){return !(t[9]&0x4800)&&up(t);}
function allbounds(){
 const pts=[];for(const t of map.floors)if(validfloor(t))for(let j=0;j<9;j+=3)pts.push(project(t.slice(j,j+3)));
 // Always keep the stored reference points in frame, including under/over ground anchors.
 for(const p of map.points)pts.push(project(p.xyz));
 for(const p of planner?.all()||[])if(p.map===map.meta.id)pts.push(project(p.xyz));
 if(!pts.length)pts.push([0,0],[100,100]);
 const xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]);return [Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)];
}
function layout(){
 const r=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;canvas.width=Math.round(r.width*dpr);canvas.height=Math.round(r.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
 const [x0,y0,x1,y1]=bounds,w=r.width,h=r.height,s=Math.min((w-70)/Math.max(100,x1-x0),(h-70)/Math.max(100,y1-y0))*zoom;
 view={w,h,s,cx:(x0+x1)/2,cy:(y0+y1)/2};
}
function xy(p){const a=project(p);return [(a[0]-view.cx)*view.s+view.w/2+pan[0],(a[1]-view.cy)*view.s+view.h/2+pan[1]];}
function terrain(t,lo,hi){
 if(t[9]&1)return '#adcbd0';
 if(style==='A')return '#dce3d5';
 const y=(t[1]+t[4]+t[7])/3,n=Math.max(0,Math.min(1,(y-lo)/Math.max(1,hi-lo)));
 return `hsl(${100-65*n} ${17+7*n}% ${83-22*n}%)`;
}
function polygon(t,fill,outline=false){ctx.beginPath();for(let j=0;j<9;j+=3){const p=xy(t.slice(j,j+3));j?ctx.lineTo(...p):ctx.moveTo(...p);}ctx.closePath();ctx.fillStyle=fill;ctx.fill();if(outline){ctx.strokeStyle='#5e735332';ctx.lineWidth=.5;ctx.stroke();}}
function symbol(p,x,y,r){
 const c=colors[owner(p)]||colors.Unknown;ctx.strokeStyle='#263d35';ctx.lineWidth=1.3;ctx.fillStyle=c;ctx.beginPath();
 if(['gb','fairy','crown','quest'].includes(p.kind)){
  const n=p.kind==='gb'?5:4;for(let i=0;i<n*2;i++){const a=i*Math.PI/n-Math.PI/2,s=i%2?r*.45:r;const px=x+Math.cos(a)*s,py=y+Math.sin(a)*s;i?ctx.lineTo(px,py):ctx.moveTo(px,py);}ctx.closePath();
 }else if(['bunch','blueprint','medal','bonus'].includes(p.kind)){
  if(p.kind==='bunch'){ctx.moveTo(x,y-r);ctx.lineTo(x+r,y);ctx.lineTo(x,y+r);ctx.lineTo(x-r,y);ctx.closePath();}else ctx.rect(x-r*.8,y-r*.8,r*1.6,r*1.6);
 }else if(p.kind==='supply'||p.kind==='landmark'||p.kind==='exit'){
  ctx.moveTo(x-r,y);ctx.lineTo(x+r,y);ctx.moveTo(x,y-r);ctx.lineTo(x,y+r);ctx.stroke();return;
 }else ctx.arc(x,y,r,0,Math.PI*2);
 ctx.fill();ctx.stroke();
 if(['coin','balloon','rainbow'].includes(p.kind)){ctx.beginPath();ctx.arc(x,y,r*.45,0,Math.PI*2);ctx.stroke();}
 if(p.kind==='bonus'){ctx.fillStyle='#263d35';ctx.font='bold 8px system-ui';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('B',x,y);}
}
function draw(){
 if(!map||!bounds)return;layout();ctx.fillStyle=style==='C'?'#eaf0e8':'#f1f3eb';ctx.fillRect(0,0,view.w,view.h);
 const [lo,hi]=height();
 // Grid in game X/Z units for actual top-down plans.
 if(style!=='C'){
  let step=1000;while(step*view.s<55)step*=2;while(step*view.s>200)step/=2;
  ctx.strokeStyle='#d4ddcd';ctx.lineWidth=.6;ctx.fillStyle='#8d9c86';ctx.font='9px system-ui';ctx.textAlign='left';ctx.textBaseline='top';
  for(let x=Math.floor(bounds[0]/step)*step;x<=bounds[2];x+=step){const a=xy([x,0,bounds[1]]);ctx.beginPath();ctx.moveTo(a[0],0);ctx.lineTo(a[0],view.h);ctx.stroke();ctx.fillText('X '+x,a[0]+3,5);}
  for(let z=Math.floor(bounds[1]/step)*step;z<=bounds[3];z+=step){const a=xy([bounds[0],0,z]);ctx.beginPath();ctx.moveTo(0,a[1]);ctx.lineTo(view.w,a[1]);ctx.stroke();ctx.fillText('Z '+z,5,a[1]+3);}
 }
 const cacheKey=map.meta.id+':'+lo+':'+hi;
 if(terrainCache?.key!==cacheKey){
  const fs=map.floors.filter(t=>validfloor(t)&&Math.min(t[1],t[4],t[7])<=hi&&Math.max(t[1],t[4],t[7])>=lo).sort((a,b)=>(a[1]+a[4]+a[7])-(b[1]+b[4]+b[7]));
  const allY=map.floors.filter(validfloor).map(t=>(t[1]+t[4]+t[7])/3),yl=allY.length?Math.min(...allY):0,yh=allY.length?Math.max(...allY):100;
  const edges=new Map();for(const t of fs){const ps=[t.slice(0,3),t.slice(3,6),t.slice(6,9)];for(let i=0;i<3;i++){const a=ps[i],b=ps[(i+1)%3],key=[a.join(','),b.join(',')].sort().join('|');const old=edges.get(key);if(old)old.count++;else edges.set(key,{a,b,count:1});}}
  terrainCache={key:cacheKey,fs,yl,yh,edges};
 }
 const {fs,yl,yh,edges}=terrainCache;
 for(const t of fs)polygon(t,terrain(t,yl,yh),style==='C');
 ctx.strokeStyle=style==='A'?'#87977c':'#77876c';ctx.lineWidth=.8;ctx.beginPath();for(const e of edges.values())if(e.count===1){ctx.moveTo(...xy(e.a));ctx.lineTo(...xy(e.b));}ctx.stroke();
 hit=[];const rank=p=>['single','coin'].includes(p.kind)?0:1;
 const pts=visible().sort((a,b)=>rank(a)-rank(b)||a.id.localeCompare(b.id));
 for(const p of pts){const [x,y]=xy(p.xyz);const r=p.kind==='single'?2.8:p.kind==='coin'?4:p.kind==='bunch'?4.3:p.kind==='balloon'?6:7;
  symbol(p,x,y,r);hit.push({p,x,y,r:r+5});
  if($('labels').checked&&!['single','coin','supply'].includes(p.kind)){ctx.font='9px system-ui';ctx.textAlign='left';ctx.textBaseline='middle';ctx.lineWidth=3;ctx.strokeStyle='#fbfcf7';const text=p.id.split('-').slice(1).join('-');ctx.strokeText(text,x+r+3,y);ctx.fillStyle='#263c31';ctx.fillText(text,x+r+3,y);}
 }
 if(filteredOwners.has('Krusha'))for(const p of planner?.all()||[]){
  if(p.map!==map.meta.id||p.xyz[1]<lo||p.xyz[1]>hi)continue;
  const [x,y]=xy(p.xyz),chosen=planner.current()?.id===p.id;
  ctx.beginPath();ctx.arc(x,y,chosen?13:10,0,Math.PI*2);ctx.fillStyle=chosen?'#e9c55e':'#ffffffcc';ctx.fill();
  symbol({...p,owner:'Krusha'},x,y,7);hit.push({p,x,y,r:12,proposal:true});
  ctx.font='bold 10px system-ui';ctx.textAlign='left';ctx.textBaseline='middle';ctx.lineWidth=3;ctx.strokeStyle='#fff';
  if(chosen||$('labels').checked||!['single','coin'].includes(p.kind)){
  const text=p.label+(p.quantity>1?' ×'+p.quantity:'');ctx.strokeText(text,x+13,y);ctx.fillStyle='#263c31';ctx.fillText(text,x+13,y);
  }
 }
 ctx.fillStyle='#2b4e3e';ctx.font='bold 11px system-ui';ctx.textAlign='right';ctx.textBaseline='bottom';ctx.fillText(style==='C'?'C · ROTATION '+Math.round(yaw)+'°':style+' · TOP DOWN / −Z UP',view.w-12,view.h-12);
 if(!map.floors.length){ctx.textAlign='center';ctx.fillText('No collision-floor geometry in this map slot',view.w/2,view.h/2);}
}
function inspect(p){selected=p;const d=$('detail');d.replaceChildren();const title=document.createElement('strong');title.textContent=p.name;d.append(title);for(const text of [p.id,'Owner: '+(p.owner||'not resolved / shared'),`X ${p.xyz[0]} · Y ${p.xyz[1]} · Z ${p.xyz[2]}`,`Source: ${p.source} #${p.index}${p.object_id==null?'':' · object '+p.object_id}`,p.flag==null?'':`Permanent flag: 0x${p.flag.toString(16)}`,p.position_note||''])if(text){const r=document.createElement('div');r.textContent=text;d.append(r);}
 if(p.kind==='exit'&&![17,20].includes(p.trigger_type)){const b=document.createElement('button');b.textContent='Open destination map';b.onclick=()=>load(p.destination);d.append(b);}}
function refresh(){
 if(!map)return;draw();const pts=visible();$('count').textContent=pts.length+' visible markers (not total rewards)';$('items').replaceChildren();
 for(const p of pts){const b=document.createElement('button');b.className='itemrow';b.textContent=`${p.owner||'—'} · ${p.name} / ${p.id}`;b.onclick=()=>{inspect(p);const a=project(p.xyz);pan=[-(a[0]-view.cx)*view.s,-(a[1]-view.cy)*view.s];draw();};$('items').append(b);}
 $('summary').textContent=`${map.meta.points} reference markers · ${map.floors.length.toLocaleString()} unique floor triangles`;
}
function fullheight(){const ys=map.points.map(p=>p.xyz[1]);for(const t of map.floors)if(validfloor(t))ys.push(t[1],t[4],t[7]);for(const p of planner?.all()||[])if(p.map===map.meta.id)ys.push(p.xyz[1]);if(!ys.length)ys.push(0,100);$('miny').value=Math.floor(Math.min(...ys)-30);$('maxy').value=Math.ceil(Math.max(...ys)+30);}
async function load(id){
 const token=++request;const script=document.createElement('script');script.src=`data/${String(id).padStart(3,'0')}.js`;
 await new Promise((resolve,reject)=>{script.onload=resolve;script.onerror=reject;document.body.append(script);}).catch(()=>{$('mapname').textContent='Could not load local map file';});script.remove();if(token!==request)return;
 if(window.ATLAS_MAP?.meta.id!==id)return;map=window.ATLAS_MAP;selected=null;zoom=1;pan=[0,0];fullheight();bounds=allbounds();$('mapname').textContent=map.meta.name;$('group').textContent=map.meta.group;$('mapid').textContent='MAP '+String(id).padStart(3,'0');$('detail').textContent='Click a symbol or an item row to inspect its coordinates.';nav();styles();refresh();planner.mapChanged();
 const url=new URL(location);url.searchParams.set('map',id);url.searchParams.set('style',style);url.searchParams.set('yaw',Math.round(yaw));history.replaceState(null,'',url);
 window.ATLAS_READY={map:id,style,yaw,points:map.points.length};
}
function styles(){for(const b of document.querySelectorAll('[data-style]'))b.classList.toggle('active',b.dataset.style===style);$('place').disabled=style==='C'||!!planner?.moveOnly();if(style==='C')$('place').checked=false;$('rotation-controls').hidden=style!=='C';$('yaw').value=yaw;$('yaw-value').value=Math.round(yaw)+'°';planner?.viewChanged();$('coords').textContent=style==='C'?'Oblique view · rotation '+Math.round(yaw)+'°':'Top: −Z · right: +X · game coordinates';}
for(const b of document.querySelectorAll('[data-style]'))b.onclick=()=>{style=b.dataset.style;zoom=1;pan=[0,0];if(map)bounds=allbounds();styles();draw();const url=new URL(location);url.searchParams.set('style',style);url.searchParams.set('yaw',Math.round(yaw));history.replaceState(null,'',url);if(window.ATLAS_READY)window.ATLAS_READY.style=style;};
function nearest(x,y,proposalsOnly=false){let best=null,distance=Infinity;for(const h of hit){if(proposalsOnly&&!h.proposal)continue;const d=Math.hypot(h.x-x,h.y-y);if(d<h.r&&d<distance){distance=d;best=h;}}return best;}
canvas.onpointerdown=e=>{drag={x:e.offsetX,y:e.offsetY,pan:[...pan],moved:false};canvas.setPointerCapture(e.pointerId);};
canvas.onpointermove=e=>{
 if(drag){const dx=e.offsetX-drag.x,dy=e.offsetY-drag.y;drag.moved||=Math.hypot(dx,dy)>4;if(drag.moved){pan=[drag.pan[0]+dx,drag.pan[1]+dy];draw();}return;}
 const h=nearest(e.offsetX,e.offsetY),tip=$('tooltip');tip.hidden=!h;if(h){tip.textContent=h.proposal?`Krusha · ${h.p.label} · ${planner.types[h.p.kind][0]} · Y ${h.p.xyz[1]}`:`${h.p.owner||'—'} · ${h.p.name} · Y ${h.p.xyz[1]}`;tip.style.left=Math.min(e.offsetX+15,view.w-220)+'px';tip.style.top=Math.max(0,e.offsetY-35)+'px';}
 if(style!=='C'&&view){const x=(e.offsetX-view.w/2-pan[0])/view.s+view.cx,z=(e.offsetY-view.h/2-pan[1])/view.s+view.cy;$('coords').textContent=`X ${Math.round(x)} · Z ${Math.round(z)} · height selected separately`;}
};
canvas.onpointerleave=()=>{$('tooltip').hidden=true;};
canvas.onpointerup=e=>{if(!drag)return;const click=!drag.moved;drag=null;if(!click)return;
 const proposal=nearest(e.offsetX,e.offsetY,true);
 if(proposal&&!planner.moving()&&!e.shiftKey){planner.select(proposal.p.id);return;}
 if(style==='A'&&($('place').checked||planner.moving())){
  const x=(e.offsetX-view.w/2-pan[0])/view.s+view.cx,z=(e.offsetY-view.h/2-pan[1])/view.s+view.cy;
  planner.placeAt(x,z);
 }else{const h=nearest(e.offsetX,e.offsetY);if(h){h.proposal?planner.select(h.p.id):inspect(h.p);}}

};
canvas.onpointercancel=()=>{drag=null;};
canvas.addEventListener('wheel',e=>{e.preventDefault();const old=zoom;zoom=Math.max(.3,Math.min(30,zoom*Math.exp(-e.deltaY*.001)));const f=zoom/old;pan=[e.offsetX-view.w/2-(e.offsetX-view.w/2-pan[0])*f,e.offsetY-view.h/2-(e.offsetY-view.h/2-pan[1])*f];draw();},{passive:false});
$('zoomin').onclick=()=>{zoom=Math.min(30,zoom*1.4);draw();};$('zoomout').onclick=()=>{zoom=Math.max(.3,zoom/1.4);draw();};$('fit').onclick=()=>{zoom=1;pan=[0,0];if(map)bounds=allbounds();draw();};
for(const id of ['miny','maxy','labels'])$(id).addEventListener('change',()=>{refresh();planner.bandChanged();});$('allheights').onclick=()=>{fullheight();refresh();planner.bandChanged();};$('search').oninput=nav;
function download(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('png').onclick=()=>{
 const output=document.createElement('canvas');output.width=canvas.width;output.height=canvas.height+130;const c=output.getContext('2d');c.fillStyle='#fafbf5';c.fillRect(0,0,output.width,output.height);c.fillStyle='#214833';c.font='bold 22px system-ui';c.fillText(map.meta.name+' — style '+style+(style==='C'?' / '+Math.round(yaw)+'°':''),20,32);c.font='12px system-ui';c.fillText('Original USA reference · '+$('miny').value+' ≤ Y ≤ '+$('maxy').value+' · user pins are proposals',20,56);c.drawImage(canvas,0,75);c.font='12px system-ui';let x=20;for(const k of Object.keys(colors)){c.fillStyle=colors[k];c.fillRect(x,output.height-31,12,12);c.fillStyle='#284131';c.fillText(k,x+17,output.height-20);x+=k.length*7+51;}
 output.toBlob(b=>download(b,`dk64-map-${map.meta.id}-${style}.png`));
};
// Interpolate native collision floors at X/Z. A narrowed Y band selects lower levels.
function surfaces(x,z){
 const result=[];
 for(const t of map.floors){
  if(!validfloor(t))continue;
  const ax=t[0],az=t[2],bx=t[3],bz=t[5],cx=t[6],cz=t[8];
  const det=(bz-cz)*(ax-cx)+(cx-bx)*(az-cz);if(Math.abs(det)<1e-8)continue;
  const a=((bz-cz)*(x-cx)+(cx-bx)*(z-cz))/det,b=((cz-az)*(x-cx)+(ax-cx)*(z-cz))/det,c=1-a-b;
  if(a>=-1e-6&&b>=-1e-6&&c>=-1e-6){const y=a*t[1]+b*t[4]+c*t[7];if(!result.some(v=>Math.abs(v-y)<.5))result.push(y);}
 }
 return result.sort((a,b)=>b-a);
}
let rotationFrame=null;
function rotate(value){
 yaw=((Number(value)%360)+360)%360;cosYaw=Math.cos(yaw*Math.PI/180);sinYaw=Math.sin(yaw*Math.PI/180);
 styles();if(map)bounds=allbounds();if(rotationFrame===null)rotationFrame=requestAnimationFrame(()=>{rotationFrame=null;draw();});
 if(window.ATLAS_READY)window.ATLAS_READY.yaw=yaw;
 const url=new URL(location);url.searchParams.set('yaw',Math.round(yaw));history.replaceState(null,'',url);
}
$('yaw').oninput=e=>rotate(e.target.value);
$('yaw-left').onclick=()=>rotate(yaw-90);$('yaw-right').onclick=()=>rotate(yaw+90);$('yaw-reset').onclick=()=>rotate(45);
planner=createKrushaPlanner({catalog,sourceSha1:ATLAS_CATALOG.source_sha1,map:()=>map,style:()=>style,height,surfaces,change:draw,download,openMap:load,
 focus:point=>{const a=project(point);pan=[-(a[0]-view.cx)*view.s,-(a[1]-view.cy)*view.s];draw();}});
$('place').onchange=()=>planner.message($('place').checked?'Click map A to add '+planner.types[$('brush-kind').value][0]+'. Click an existing proposal to edit; Shift+click adds at the same point.':'Select a proposal to edit it.');
new ResizeObserver(()=>draw()).observe($('stage'));
nav();load(params.has('map')&&catalog.some(m=>m.id===Number(params.get('map')))?Number(params.get('map')):7);
})();
