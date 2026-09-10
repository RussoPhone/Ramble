const actions={move:'mover',turn:'girar',wait:'esperar',inspect:'inspecionar',touch:'tocar',
  ingest:'ingerir',pick:'pegar',drop:'soltar',place:'colocar',give:'transferir',signal:'emitir sinal',
  birth:'nascimento',death:'morte'};
export const actionLabel=action=>actions[action]||action||'nenhuma';
export const patternLabel=signature=>signature?.length?signature.join(' · '):'sem assinatura';
const signed=value=>value<0?`−${Number(Math.abs(value).toFixed(1))}`:value>0?`+${Number(value.toFixed(1))}`:'0';
export const deltaLabel=delta=>delta?`fome ${signed(delta[0])} · sede ${signed(delta[1])}`:'efeito corporal não conhecido';
export const experienceOutcome=e=>e.success==null?'resultado não observado':e.success?'ação efetivada':'ação não efetivada';
export const sourceLabel=source=>source==='self'?'própria':source==='observed'?'observada':source;
export const layerLabel=layer=>({agent:'indivíduo',object:'objeto',terrain:'terreno'})[layer]||layer;
export const directionLabel=o=>({'0,-1':'norte ↑','1,0':'leste →','0,1':'sul ↓','-1,0':'oeste ←'})[o?.join(',')]||o?.join(', ');
