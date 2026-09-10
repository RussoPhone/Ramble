import { ObserverTransport } from './transport.mjs';
import { SimulationStore } from './store.mjs';
import { fitCamera,panCamera,zoomCameraAt,centerCameraOn } from './camera.mjs';
import { candidatesAt,resolveSelection,selectionKey } from './selection.mjs';
import { assertRenderer } from './renderers/renderer-contract.mjs';
import { AsciiRenderer,paintAsciiPreview } from './renderers/ascii-renderer.mjs';
import { renderInspector } from './ui/inspector.mjs';
import { renderAgentHistory } from './ui/agent-history.mjs';
import { layerLabel } from './ui/inspection-format.mjs';
import { parseTickRate } from './control-values.mjs';

const $=id=>document.getElementById(id),canvas=$('world-canvas');
const transport=new ObserverTransport(),store=new SimulationStore();
const ui={camera:null,selection:null,cell:null,detail:null,following:false,
  tab:'summary',reading:null,readingLoading:false,readingError:'',showCollisions:false,showVision:false};
let readingRequest=0;
let renderer,snapshotAt=0,dirty=true,pollQueued=false,controlBusy=false;
let tail=Promise.resolve(),timer=null;
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
const viewport=()=>({width:canvas.clientWidth,height:canvas.clientHeight,ratio:Math.min(devicePixelRatio||1,2)});
const enqueue=task=>{const result=tail.then(task,task);tail=result.catch(()=>{});return result;};

function error(message=''){$('error-banner').textContent=message;$('error-banner').hidden=!message;}
function fit(){if(store.scene){const v=viewport();ui.camera=fitCamera(store.scene.width,store.scene.height,v.width,v.height,16);dirty=true;}}
function paintKey(){
  for(const symbol of document.querySelectorAll('[data-symbol]')){
    const [layer,kind]=symbol.dataset.symbol.split(':');paintAsciiPreview(symbol,{layer,kind});
  }
}
function resetReading(){readingRequest++;ui.tab='summary';ui.reading=null;ui.readingLoading=false;ui.readingError='';}
function visionCells(){
  if(!ui.showVision||!Array.isArray(ui.detail?.vision))return null;
  return resolveSelection(store.scene,ui.selection)?.layer==='agent'?ui.detail.vision:null;
}
function clearSelection(){ui.selection=null;ui.cell=null;ui.detail=null;ui.following=false;resetReading();chrome();dirty=true;}
function chrome(forceSpeed=false){
  const scene=store.scene;if(!scene)return;
  const control=scene.control;
  const runState=control.running?'running':control.remaining?'burst':'paused';
  $('world-dimensions').textContent=`${scene.width} × ${scene.height}`;
  $('tick-value').textContent=`tick ${scene.tick}`;
  $('population-value').textContent=`${scene.agents.length} vivos`;
  $('run-state').textContent=runState==='running'?'EM CURSO':runState==='burst'?'RAJADA':'PAUSADA';
  $('run-state').dataset.state=runState;
  $('remaining-value').textContent=control.remaining?`${control.remaining} ticks restantes`:`${control.speed} ticks/s`;
  if(forceSpeed||document.activeElement!==$('speed-value'))$('speed-value').value=String(control.speed);
  $('step-button').disabled=controlBusy||control.running||control.remaining>0;
  $('run-button').classList.toggle('active',control.running);
  $('pause-button').classList.toggle('active',!control.running&&!control.remaining);
  const item=resolveSelection(scene,ui.selection);
  if(ui.selection&&!item){ui.selection=null;ui.following=false;ui.detail=null;resetReading();}
  $('follow-agent').disabled=item?.layer!=='agent';
  $('follow-agent').classList.toggle('active',ui.following);
  renderInspector($('inspector'),scene,item,ui.detail,{tab:ui.tab});
  if(item?.layer==='agent'&&ui.tab!=='summary'){
    $('reading-tick').textContent=ui.reading?`leitura fixada · tick ${ui.reading.tick}`:'leitura sob demanda';
    $('refresh-inspection').disabled=ui.readingLoading;
    $('history-status').textContent=ui.readingLoading?'Lendo registros…':ui.readingError;
    renderAgentHistory($('history-content'),ui.reading?.detail,ui.tab);
  }
  const candidates=$('selection-candidates');
  if(item) {
    // A selected entity follows its real cell; terrain selection stays fixed.
    ui.cell={x:item.x,y:item.y};
    const current=new Map([...candidates.children].map(button=>
      [`${button.dataset.layer}:${button.dataset.id}`,button]));
    const ordered=[];
    for(const candidate of candidatesAt(scene,item.x,item.y)){
      const key=`${candidate.layer}:${candidate.id}`;
      const button=current.get(key)||document.createElement('button');
      if(!current.has(key)){
        const layer=document.createElement('span'),name=document.createElement('span'),id=document.createElement('span');
        layer.className='candidate-layer';id.className='candidate-id';button.append(layer,name,id);
        button.dataset.layer=candidate.layer;button.dataset.id=candidate.id;
        button.addEventListener('click',()=>select({layer:candidate.layer,id:candidate.id}));
      }
      const parts=button.children;
      parts[0].textContent=layerLabel(candidate.layer);parts[1].textContent=candidate.kind;
      parts[2].textContent=candidate.layer==='terrain'?'':`#${candidate.id}`;
      button.classList.toggle('active',candidate.layer===item.layer&&candidate.id===item.id);
      current.delete(key);ordered.push(button);
    }
    for(const button of current.values())button.remove();
    ordered.forEach((button,index)=>{if(candidates.children[index]!==button)
      candidates.insertBefore(button,candidates.children[index]||null);});
  } else {
    candidates.replaceChildren();
  }
}
function select(item){ui.selection=selectionKey(item);ui.detail=null;ui.following=false;resetReading();chrome();dirty=true;poll();}
function loadReading(){
  const item=resolveSelection(store.scene,ui.selection),tab=ui.tab;
  if(item?.layer!=='agent'||tab==='summary')return;
  const revision=store.scene.worldRevision,request=++readingRequest;
  ui.readingLoading=true;ui.readingError='';chrome();
  enqueue(async()=>{
    try{
      const result=await transport.detail(item,tab);
      if(request!==readingRequest)return;
      if(result.schemaVersion!==store.scene.schemaVersion||result.worldRevision!==revision||revision!==store.scene.worldRevision)
        throw new Error('O mundo mudou. Selecione novamente o gaiano.');
      if(!result.detail||result.detail.agentId!==item.id)throw new Error('Este gaiano não está mais disponível.');
      ui.reading=result;
    }catch(e){if(request===readingRequest)ui.readingError=`Não foi possível atualizar: ${e.message}`;}
    finally{if(request===readingRequest){ui.readingLoading=false;chrome();}}
  });
}
function setTab(tab){
  if(resolveSelection(store.scene,ui.selection)?.layer!=='agent')return;
  if(ui.tab===tab)return;
  resetReading();ui.tab=tab;chrome();if(tab!=='summary')loadReading();
}
function accept(data,bootstrap=false){
  const oldRevision=store.scene?.worldRevision;
  if(bootstrap)store.bootstrap(data);
  else if(store.applyFrame(data)==='resync')return false;
  if(oldRevision&&oldRevision!==store.scene.worldRevision){ui.selection=null;ui.detail=null;ui.camera=null;ui.following=false;resetReading();}
  snapshotAt=performance.now();
  if(!ui.camera)fit();
  if(ui.following){const a=resolveSelection(store.scene,ui.selection);if(a)ui.camera=centerCameraOn(ui.camera,a.x,a.y,viewport());}
  chrome();dirty=true;return true;
}
function poll(){
  if(pollQueued)return;
  pollQueued=true;
  enqueue(async()=>{
    try{
      const initial=!store.scene;
      const data=await(initial?transport.bootstrap():transport.frame());
      if(!accept(data,initial))accept(await transport.bootstrap(),true);
      $('connection-label').textContent='conectado';
      $('connection-label').dataset.state='connected';
      error(store.scene.control.error?`Simulação interrompida: ${store.scene.control.error}`:'');
      const item=resolveSelection(store.scene,ui.selection);
      if(item){
        const selected=ui.selection,revision=store.scene.worldRevision;
        const detail=await transport.detail(item);
        if(selected===ui.selection&&revision===detail.worldRevision&&detail.tick>=store.scene.tick){
          ui.detail=detail.detail;chrome();
        }
      }
    }catch(e){
      $('connection-label').textContent='reconectando';
      $('connection-label').dataset.state='reconnecting';
      error(`Última cena preservada. ${e.message}`);
    }
    finally{pollQueued=false;}
  });
}
function control(command,value,{restoreSpeed=false}={}){
  if(controlBusy)return;
  controlBusy=true;
  for(const el of document.querySelectorAll('#time-controls button, #time-controls input, #time-controls select'))el.disabled=true;
  enqueue(async()=>{
    try{await transport.control(command,value);error();}
    catch(e){error(e.message);}
    finally{controlBusy=false;for(const el of document.querySelectorAll('#time-controls button, #time-controls input, #time-controls select'))el.disabled=false;chrome(restoreSpeed);poll();}
  });
}
let pointer=null;
canvas.addEventListener('pointerdown',e=>{
  if(e.button!==0)return;canvas.focus();
  pointer={id:e.pointerId,startX:e.clientX,startY:e.clientY,x:e.clientX,y:e.clientY,moved:false};
  canvas.setPointerCapture(e.pointerId);
});
canvas.addEventListener('pointermove',e=>{
  if(!ui.camera)return;
  const rect=canvas.getBoundingClientRect();
  if(pointer&&pointer.id===e.pointerId){
    const dx=e.clientX-pointer.x,dy=e.clientY-pointer.y;
    if(Math.hypot(e.clientX-pointer.startX,e.clientY-pointer.startY)>4)pointer.moved=true;
    if(pointer.moved){ui.camera=panCamera(ui.camera,dx,dy);ui.following=false;dirty=true;}
    pointer.x=e.clientX;pointer.y=e.clientY;
  }else{
    const candidates=renderer.hitTest({x:e.clientX-rect.left,y:e.clientY-rect.top});
    const item=candidates[0];
    $('world-hover').textContent=item
      ?`[${item.kind}] · ${item.x}, ${item.y}`
      :'';
  }
});
canvas.addEventListener('pointerup',e=>{
  if(!pointer||pointer.id!==e.pointerId)return;
  if(!pointer.moved){const rect=canvas.getBoundingClientRect();const hit=renderer.hitTest({x:e.clientX-rect.left,y:e.clientY-rect.top});if(hit.length)select(hit[0]);else clearSelection();}
  canvas.releasePointerCapture(e.pointerId);pointer=null;
});
canvas.addEventListener('pointercancel',()=>pointer=null);
canvas.addEventListener('pointerleave',()=>{$('world-hover').textContent='';});
canvas.addEventListener('wheel',e=>{
  if(!ui.camera)return;e.preventDefault();const rect=canvas.getBoundingClientRect();
  ui.camera=zoomCameraAt(ui.camera,e.clientX-rect.left,e.clientY-rect.top,e.deltaY<0?1.2:1/1.2);
  ui.following=false;dirty=true;
},{passive:false});
$('fit-world').onclick=()=>{ui.following=false;fit();};
$('close-inspector').onclick=clearSelection;
$('refresh-inspection').onclick=loadReading;
for(const button of document.querySelectorAll('[data-tab]')){
  button.onclick=()=>setTab(button.dataset.tab);
  button.addEventListener('keydown',e=>{
    if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;
    e.preventDefault();e.stopPropagation();
    const tabs=[...document.querySelectorAll('[data-tab]')],index=tabs.indexOf(button);
    const next=e.key==='Home'?0:e.key==='End'?2:(index+(e.key==='ArrowLeft'?2:1))%3;
    tabs[next].focus();setTab(tabs[next].dataset.tab);
  });
}
$('follow-agent').onclick=()=>{ui.following=!ui.following;const a=resolveSelection(store.scene,ui.selection);if(a&&ui.following)ui.camera=centerCameraOn(ui.camera,a.x,a.y,viewport());chrome();dirty=true;};
$('show-collisions').onchange=e=>{ui.showCollisions=e.target.checked;dirty=true;};
$('show-vision').onchange=e=>{ui.showVision=e.target.checked;dirty=true;if(e.target.checked)poll();};
$('seed-form').onsubmit=e=>{
  e.preventDefault();
  const raw=$('seed-value').value.trim();
  const value=raw===''?Math.floor(Math.random()*2147483648):Number(raw);
  if(!Number.isInteger(value)||value<0||value>2147483647){error('Semente deve ser um inteiro entre 0 e 2147483647.');return;}
  $('seed-value').value=String(value);
  control('regenerate',value);
};
$('run-button').onclick=()=>control('run');
$('pause-button').onclick=()=>control('pause');
$('step-button').onclick=()=>control('step');
function commitSpeed(){
  try{control('speed',parseTickRate($('speed-value').value),{restoreSpeed:true});}
  catch(e){error(e.message);chrome(true);}
}
$('speed-value').onchange=commitSpeed;
$('speed-value').onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();commitSpeed();}};
$('burst-form').onsubmit=e=>{e.preventDefault();control('burst',Number($('burst-value').value));};
document.addEventListener('keydown',e=>{
  if(['INPUT','SELECT','TEXTAREA','BUTTON','SUMMARY'].includes(e.target.tagName)||e.ctrlKey||e.metaKey||e.altKey)return;
  if(e.key==='Escape')clearSelection();
  else if(e.key===' '){e.preventDefault();control(store.scene?.control.running||store.scene?.control.remaining?'pause':'run');}
  else if(e.key==='.')control('step');
  else if(e.key==='0')fit();
  else if(e.key.toLowerCase()==='f')$('follow-agent').click();
  else if(ui.camera&&e.key.startsWith('Arrow')){
    const delta={ArrowLeft:[40,0],ArrowRight:[-40,0],ArrowUp:[0,40],ArrowDown:[0,-40]}[e.key];
    if(delta){e.preventDefault();ui.camera=panCamera(ui.camera,...delta);ui.following=false;dirty=true;}
  }
});
new ResizeObserver(()=>{renderer?.resize(viewport());dirty=true;}).observe(canvas);
function draw(now){
  const p=reducedMotion.matches?1:Math.min(1,(now-snapshotAt)/150);
  if(renderer&&ui.camera&&store.scene&&(dirty||p<1)){
    renderer.render(store.scene,ui.camera,{selection:ui.selection,previous:store.previous,
      motionProgress:p,showCollisions:ui.showCollisions,vision:visionCells()});
    $('map-scale').textContent=`1 célula · ${Math.round(ui.camera.cell)} px`;
    dirty=p<1;
  }
  requestAnimationFrame(draw);
}
async function start(){
  renderer=assertRenderer(new AsciiRenderer());
  renderer.mount(canvas);renderer.resize(viewport());
  paintKey();poll();timer=setInterval(poll,200);requestAnimationFrame(draw);
}
addEventListener('pagehide',()=>{clearInterval(timer);renderer?.dispose();});
start();
