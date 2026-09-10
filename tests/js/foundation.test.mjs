import test from 'node:test';
import assert from 'node:assert/strict';
import { SimulationStore } from '../../core/interface/static/store.mjs';
import { candidatesAt, resolveSelection } from '../../core/interface/static/selection.mjs';
import { AsciiRenderer, asciiGlyph } from '../../core/interface/static/renderers/ascii-renderer.mjs';
import { BaseRenderer } from '../../core/interface/static/renderers/base-renderer.mjs';
import { assertRenderer } from '../../core/interface/static/renderers/renderer-contract.mjs';
import { cellRecords } from '../../core/interface/static/scene-model.mjs';
import { parseTickRate } from '../../core/interface/static/control-values.mjs';

const terrain = {id:'0,0',layer:'terrain',kind:'grass',x:0,y:0,blocking:false};
const object = {id:2,layer:'object',kind:'stone',x:0,y:0,quantity:1};
const agent = {id:1,layer:'agent',kind:'gaiano',x:0,y:0,orientation:[0,-1],body:{hunger:0,thirst:0},
  micro_position:[1,1],collision_cells:[[1,1],[1,0]]};
const bootstrap = () => ({schemaVersion:2,worldRevision:'one',tick:0,width:2,height:2,
  terrain:[terrain,...[[1,0],[0,1],[1,1]].map(([x,y])=>({...terrain,id:`${x},${y}`,x,y}))],objects:[object,{...object,id:3}],agents:[agent],events:[],
  catalog:[],config:{},control:{running:false,speed:20,remaining:0}});

test('tick rate parser enforces server limits',()=>{
  assert.equal(parseTickRate('0.1'),0.1);
  assert.equal(parseTickRate('1250.5'),1250.5);
  for(const value of ['', '0', '100000.1', 'NaN', 'Infinity'])assert.throws(()=>parseTickRate(value));
});

test('store applies dynamic frames atomically and preserves static terrain',()=>{
  const s=new SimulationStore();s.bootstrap(bootstrap());
  const previous=s.scene;
  assert.equal(s.applyFrame({...bootstrap(),worldRevision:'other'}),'resync');
  assert.equal(s.scene,previous);
  assert.throws(()=>s.applyFrame({...bootstrap(),tick:1,agents:null}));
  assert.equal(s.scene,previous);
  assert.equal(s.applyFrame({...bootstrap(),tick:1,objects:[]}), 'applied');
  assert.equal(s.scene.terrain,previous.terrain);
  assert.equal(s.scene.objects.length,0);
  assert.equal(s.applyFrame({...bootstrap(),tick:0}), 'stale');
  assert.equal(s.scene.tick,1);
});

test('invalid nested data cannot replace a valid scene and schema changes request bootstrap',()=>{
  const s=new SimulationStore();s.bootstrap(bootstrap());const scene=s.scene;
  assert.throws(()=>s.applyFrame({...bootstrap(),agents:[{...agent,body:null}]}));
  assert.equal(s.scene,scene);
  assert.throws(()=>s.bootstrap({...bootstrap(),terrain:[terrain]}));
  assert.equal(s.scene,scene);
  assert.equal(s.applyFrame({...bootstrap(),schemaVersion:3}), 'resync');
  assert.throws(()=>s.bootstrap({...bootstrap(),schemaVersion:3}));
  assert.equal(s.scene,scene);
  assert.throws(()=>cellRecords(scene,0,0).pop());
});

test('store rejects malformed or inconsistent agent microcell geometry atomically',()=>{
  const invalid = [
    {...agent,micro_position:[1]},
    {...agent,collision_cells:[[1,1]]},
    {...agent,collision_cells:[[1,1],[2,2]]},
    {...agent,micro_position:[0,0],collision_cells:[[0,0],[-1,0]]},
    {...agent,x:1,micro_position:[1,1],collision_cells:[[1,1],[1,0]]},
  ];
  for (const candidate of invalid) {
    const s=new SimulationStore();s.bootstrap(bootstrap());const scene=s.scene;
    assert.throws(()=>s.applyFrame({...bootstrap(),tick:1,agents:[candidate]}));
    assert.equal(s.scene,scene);
  }
});

test('selection enumerates all layers without collapsing stacked objects',()=>{
  const s=new SimulationStore();s.bootstrap(bootstrap());
  const candidates=candidatesAt(s.scene,0,0);
  assert.deepEqual(candidates.map(c=>c.layer),['agent','object','object','terrain']);
  assert.equal(resolveSelection(s.scene,{layer:'object',id:3}).id,3);
  assert.equal(resolveSelection(s.scene,{layer:'terrain',id:'0,0'}).kind,'grass');
});

test('ascii renderer consumes a frozen scene and exposes the picking contract',()=>{
  const s=new SimulationStore();s.bootstrap(bootstrap());
  const scene=s.scene;
  const calls=[];
  const ctx=new Proxy({}, {get(target,key){return target[key]??((...args)=>calls.push([key,...args]));},set(t,k,v){t[k]=v;return true;}});
  const surface={width:0,height:0,getContext:()=>ctx};
  const options={selection:{layer:'object',id:2},motionProgress:1};
  const renderer=assertRenderer(new AsciiRenderer());renderer.mount(surface);
  renderer.resize({width:200,height:200,ratio:1});
  renderer.render(scene,{cell:24,offsetX:0,offsetY:0},options);
  assert.equal(renderer.hitTest({x:12,y:12})[0].layer,'agent');
  assert.equal(renderer.hitTest({x:22,y:22})[0].layer,'terrain');
  assert.equal(renderer.hitTest({x:150,y:150}).length,0);
  renderer.dispose();
  assert.ok(calls.some(c=>c[0]==='fillText'));
  assert.equal(s.scene,scene);
});

test('ascii renderer culls layers and picks the visible interpolated agent without changing grid state',()=>{
  const initial={...bootstrap(),agents:[{...agent,micro_position:[2,1],collision_cells:[[2,1],[2,0]]}]};
  const s=new SimulationStore();s.bootstrap(initial);
  s.applyFrame({...bootstrap(),tick:1,agents:[{...agent,x:1,micro_position:[3,1],collision_cells:[[3,1],[3,0]]}]});
  const ctx=new Proxy({}, {get(t,k){return t[k]??(()=>{});},set(t,k,v){t[k]=v;return true;}});
  const r=new AsciiRenderer(),drawn=[];
  r.mount({getContext:()=>ctx});r.resize({width:24,height:24});
  r.tile=i=>drawn.push(i);r.object=i=>drawn.push(i);r.agent=i=>drawn.push(i);
  r.render(s.scene,{cell:24,offsetX:0,offsetY:0});
  assert.ok(drawn.every(i=>i.x===0&&i.y===0));
  r.resize({width:100,height:100});
  r.render(s.scene,{cell:24,offsetX:0,offsetY:0},{previous:s.previous,motionProgress:.1});
  assert.equal(r.hitTest({x:21,y:12})[0].id,agent.id);
  assert.equal(s.scene.agents[0].x,1);
  r.dispose();
});

test('ascii renderer uses lod without inventing physical cells',()=>{
  assert.equal(asciiGlyph({...agent,cells:[[1,0],[0,1],[1,1],[2,1],[1,2]]}, 10), '@');
  assert.equal(asciiGlyph({...agent,cells:[[1,0],[0,1],[1,1],[2,1],[1,2]]}, 24), '@');
  const calls=[];
  const ctx=new Proxy({}, {get(target,key){return target[key]??((...args)=>calls.push([key,...args]));},set(t,k,v){t[k]=v;return true;}});
  const renderer=new AsciiRenderer();
  renderer.mount({width:0,height:0,getContext:()=>ctx});
  renderer.resize({width:80,height:80,ratio:1});
  renderer.agent({...agent,cells:[[1,0],[0,1],[1,1],[2,1],[1,2]],orientation:[1,0]}, {cell:48,offsetX:0,offsetY:0});

  assert.equal(calls.filter(([name])=>name==='fillRect').length, 0);
  assert.equal(calls.some(([name])=>name==='fillText'), false);
  assert.equal(calls.some(([name])=>name==='fill'), true);
});

function drawingContext(calls=[]) {
  return new Proxy({}, {
    get(target,key) {
      if (key === 'fillRect') return (...args)=>calls.push(['fillRect',target.fillStyle,...args]);
      return target[key]??((...args)=>calls.push([key,...args]));
    },
    set(target,key,value) { target[key]=value; return true; },
  });
}

test('renderer interpolates one adjacent microcell and never invents a skipped path',()=>{
  class CaptureRenderer extends BaseRenderer {
    tile(){} object(){} agent(item){this.drawn=item;}
  }
  const prior={...bootstrap(),agents:[{...agent,orientation:[1,0],micro_position:[2,1],collision_cells:[[2,1],[3,1]]}]};
  const current={...bootstrap(),tick:1,agents:[{...agent,x:1,orientation:[1,0],micro_position:[3,1],collision_cells:[[3,1],[4,1]]}]};
  const renderer=new CaptureRenderer();
  renderer.mount({getContext:()=>drawingContext()});renderer.resize({width:200,height:200});
  renderer.render(current,{cell:30,offsetX:0,offsetY:0},{previous:prior,motionProgress:.5});
  assert.deepEqual(renderer.drawn.visual_micro_position,[2.5,1]);
  assert.deepEqual(renderer.agentWorldPoint(renderer.drawn),{x:1,y:.5});
  assert.equal(renderer.agentWorldPoint({...agent,micro_position:[3,1]}).x-
    renderer.agentWorldPoint({...agent,micro_position:[0,1]}).x,1);

  renderer.render({...current,tick:2},{cell:30,offsetX:0,offsetY:0},{previous:prior,motionProgress:.5});
  assert.deepEqual(renderer.drawn.visual_micro_position,[3,1]);
});

test('close gaiano uses base and nose geometry and only draws collision cells when enabled',()=>{
  const calls=[];
  const renderer=new AsciiRenderer();
  renderer.mount({getContext:()=>drawingContext(calls)});renderer.resize({width:200,height:200});
  const data={...bootstrap(),objects:[],agents:[{...agent,orientation:[1,0],micro_position:[1,1],collision_cells:[[1,1],[2,1]]}]};
  const store=new SimulationStore();store.bootstrap(data);const scene=store.scene;
  renderer.render(scene,{cell:60,offsetX:0,offsetY:0},{showCollisions:false});
  assert.equal(calls.filter(([name,color])=>name==='fillRect'&&color==='rgba(195, 181, 151, 0.68)').length,0);
  calls.length=0;
  renderer.render(scene,{cell:60,offsetX:0,offsetY:0},{showCollisions:true});
  const collision=calls.filter(([name,color])=>name==='fillRect'&&color==='rgba(195, 181, 151, 0.68)');
  assert.deepEqual(collision.map(call=>call.slice(2)),[[20,20,20,20],[40,20,20,20]]);
  assert.equal(calls.some(([name])=>name==='fill'),true);
});
