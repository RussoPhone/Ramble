import { actionLabel, patternLabel, deltaLabel, sourceLabel, experienceOutcome } from './inspection-format.mjs';

const rendered=new WeakMap();
const node=(tag,text,className)=>{const el=document.createElement(tag);if(text!=null)el.textContent=text;if(className)el.className=className;return el;};
const field=(dl,label,value)=>dl.append(node('dt',label),node('dd',value));

function evidenceEntry(e) {
  return `tick ${e.tick} · ${sourceLabel(e.source)} · ${actionLabel(e.action)}${e.target==null?'':` #${e.target}`} · ${experienceOutcome(e)}`;
}

function memoryContent(root,data) {
  root.append(node('p',`${data.relations.length} relações / ${data.capacity} · ${data.experienceCount} experiências guardadas`,'reading-count'));
  root.append(node('p','Assinaturas são padrões aprendidos, não nomes de recursos. Os efeitos abaixo são estimativas da memória, não garantias do mundo.','reading-note'));
  if(!data.relations.length){root.append(node('p','Nenhuma relação registrada ainda. Execute alguns ticks e atualize esta leitura.','empty-reading'));return;}
  const head=node('div',null,'history-head');
  head.append(node('span','padrão'),node('span','ação'),node('span','confiança'));root.append(head);
  const list=node('ol',null,'history-list');
  for(const r of data.relations){
    const li=node('li'),details=node('details'),summary=node('summary');details.dataset.record=String(r.id);
    summary.append(node('span',patternLabel(r.signature),'pattern'),node('span',actionLabel(r.action)),
      node('span',`${Math.round(r.confidence*100)}%`,'confidence'));
    const body=node('div',null,'evidence'),dl=node('dl');
    field(dl,'relação',`#${r.id}`);
    field(dl,'efeito estimado',deltaLabel(r.delta));
    field(dl,'força',r.weight.toFixed(2));
    field(dl,'contradições',r.contradictions);
    field(dl,'última evidência',`tick ${r.lastTick} · há ${r.age} ticks`);
    field(dl,'origem',Object.entries(r.sources).map(([key,n])=>`${n} ${sourceLabel(key)}`).join(' · '));
    if(r.bodyContext)field(dl,'contexto corporal',r.bodyContext.map((b,i)=>`${i?'sede':'fome'} ${b*25}–${b*25+24}`).join(' · '));
    if(r.signal!=null)field(dl,'sinal no contexto',String(r.signal));
    body.append(dl,node('p','Evidências preservadas nesta relação'));
    const evidence=node('ul');for(const e of [...r.evidence].reverse())evidence.append(node('li',evidenceEntry(e)));
    body.append(evidence);details.append(summary,body);li.append(details);list.append(li);
  }
  root.append(list,node('p',`${data.forgotten} relações removidas da memória ao longo da execução.`,'reading-note'));
}

function logContent(root,data,source,onSource) {
  const filter=node('label',null,'log-filter');filter.append(node('span','mostrar'));
  const select=node('select');select.id='log-source';
  for(const [value,label]of [['experiences','Experiências do gaiano'],['events','Eventos físicos envolvendo o gaiano']]){
    const option=node('option',label);option.value=value;select.append(option);
  }
  select.value=source;select.addEventListener('change',()=>onSource(select.value));filter.append(select);root.append(filter);
  const experiences=source==='experiences',items=experiences?data.experiences:data.events;
  root.append(node('p',experiences?`${items.length} experiências / ${data.experienceCapacity} guardadas`:`${items.length} eventos envolvendo este gaiano`,'reading-count'));
  root.append(node('p',experiences?'Própria: tentativa do gaiano. Observada: registro de uma ação alheia; seu resultado físico pode ser desconhecido.':`Visão física do pesquisador. Recorte dos últimos ${data.eventCapacity} eventos globais, não um histórico completo da vida.`,'reading-note'));
  if(!items.length){root.append(node('p','Nenhum registro disponível neste recorte.','empty-reading'));return;}
  const list=node('ol',null,'history-list log-list');
  for(const [i,e] of [...items].reverse().entries()){
    const li=node('li'),details=node('details'),summary=node('summary');details.dataset.record=`${source}-${i}`;
    summary.append(node('span',`t ${e.tick}`,'log-tick'),node('span',`${actionLabel(e.action)}${e.target==null?'':` → #${e.target}`}`,'pattern'));
    summary.append(node('span',experiences?`${sourceLabel(e.source)} · ${experienceOutcome(e)}`:`agente #${e.actor}${e.child?` · descendente #${e.child}`:''}`,'log-meta'));
    const body=node('div',null,'evidence'),dl=node('dl');
    field(dl,'ator',e.actor==null?'não registrado':`#${e.actor}`);
    if(experiences){field(dl,'padrão',patternLabel(e.signature));field(dl,'delta corporal',deltaLabel(e.delta));}
    else {
      if(e.position)field(dl,'posição no mundo',e.position.join(', '));
      if(e.delta)field(dl,'delta corporal',deltaLabel(e.delta));
      if(e.child)field(dl,'descendente',`#${e.child}`);
    }
    body.append(dl);details.append(summary,body);li.append(details);list.append(li);
  }
  root.append(list);
}

export function renderAgentHistory(root,data,section,force=false) {
  const previous=rendered.get(root);
  if(!force&&previous?.data===data&&previous?.section===section)return;
  const open=new Set([...root.querySelectorAll('details[open]')].map(el=>el.dataset.record));
  const state={data,section,source:previous?.source||'experiences'};
  rendered.set(root,state);root.replaceChildren();
  if(!data)return;
  if(section==='memory')memoryContent(root,data);
  else logContent(root,data,state.source,source=>{state.source=source;renderAgentHistory(root,data,section,true);});
  for(const detail of root.querySelectorAll('details'))detail.open=open.has(detail.dataset.record);
}
