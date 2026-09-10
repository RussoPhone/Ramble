// Optional browser verification; no production dependency or screenshots.
// GAEA_PLAYWRIGHT_MODULE=/absolute/path/playwright/index.mjs node tests/browser/observer-smoke.mjs
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';

const { chromium } = await import(process.env.GAEA_PLAYWRIGHT_MODULE || 'playwright');
const root = fileURLToPath(new URL('../../', import.meta.url));
// A real runtime with a controlled initial physical scene, not a mocked API.
// Two immovable stones guarantee a persistent multi-object cell during the test.
const fixture = `
from core.simulation.population import PopulationConfig, PopulationSimulation
from core.interface.server import create_server
from core.ambient.tile import WATER
s = PopulationSimulation(PopulationConfig(width=18, height=14, population=8,
    objects=45, stones=5, metabolism=0, reproduction=False))
a = next(iter(s.agents.values()))
for _ in range(2):
    s.add_object(a.x, a.y, (41, 9, 1), portable=False, ingestible=False, kind='stone')
s.world.set_tile(1, 1, WATER)
server = create_server(s, port=0)
print(server.server_address[1], flush=True)
server.serve_forever()
`;
const server = spawn(process.env.PYTHON || 'python', ['-c', fixture], { cwd: root, stdio: ['ignore','pipe','inherit'] });
const lines = createInterface({ input: server.stdout });
let browser;
try {
  const [port] = await Promise.race([
    once(lines, 'line'),
    once(server, 'exit').then(([code])=>{throw new Error(`Fixture exited: ${code}`);}),
  ]);
  const url = `http://127.0.0.1:${port}`;
  browser = await chromium.launch({ headless: true,
    ...(process.env.GAEA_CHROMIUM ? { executablePath: process.env.GAEA_CHROMIUM } : {}) });
  const page = await browser.newPage({ viewport: {width:1280,height:800} });
  const failures=[], requests=[];
  page.on('pageerror', e=>failures.push(e.message));
  page.on('request', r=>requests.push(new URL(r.url()).pathname));
  const frame = async()=> (await fetch(`${url}/api/frame`)).json();
  const uiTick = async()=> Number((await page.locator('#tick-value').innerText()).split(' ')[1]);
  const waitTick = tick=>page.waitForFunction(t=>Number(document.querySelector('#tick-value').textContent.split(' ')[1])===t,tick);
  await page.goto(url);
  await page.waitForFunction(()=>document.querySelector('#connection-label').textContent==='conectado');
  const bootstrap = await (await fetch(`${url}/api/bootstrap`)).json();
  assert.equal(await uiTick(),0);
  assert.equal(await page.locator('#inspector').isVisible(),false);
  assert.equal(await page.locator('#show-collisions').isChecked(),false);
  const box = await page.locator('#world-canvas').boundingBox();
  assert.ok(box.width*box.height/(1280*800)>=.85);
  const collisionFrame=await frame();
  const canvasBefore=await page.locator('#world-canvas').evaluate(canvas=>canvas.toDataURL());
  await page.locator('#show-collisions').check();
  await page.waitForTimeout(100);
  const canvasAfter=await page.locator('#world-canvas').evaluate(canvas=>canvas.toDataURL());
  assert.notEqual(canvasAfter,canvasBefore);
  assert.deepEqual(await frame(),collisionFrame,'collision overlay must be purely observational');
  await page.waitForTimeout(250);
  assert.equal(await page.locator('#show-collisions').isChecked(),true);

  await page.locator('#run-button').click();
  await page.waitForFunction(()=>Number(document.querySelector('#tick-value').textContent.split(' ')[1])>=4);
  await page.locator('#pause-button').click();
  await page.waitForFunction(()=>document.querySelector('#run-state').textContent==='PAUSADA');
  let paused=await frame();
  await page.waitForTimeout(350);
  assert.equal((await frame()).tick,paused.tick);
  await page.locator('#step-button').click();
  await waitTick(paused.tick+1);
  await page.locator('#speed-value').fill('37.5');
  await page.locator('#speed-value').press('Enter');
  await page.waitForFunction(()=>document.querySelector('#remaining-value').textContent==='37.5 ticks/s');
  assert.equal((await frame()).control.speed,37.5);
  assert.equal(await page.locator('#speed-value').inputValue(),'37.5');
  await page.locator('#speed-value').fill('100000.1');
  await page.locator('#speed-value').press('Enter');
  await page.waitForTimeout(100);
  assert.equal((await frame()).control.speed,37.5);
  assert.equal(await page.locator('#speed-value').inputValue(),'37.5');
  paused=await frame();
  await page.locator('#burst-value').fill('3');
  await page.locator('#burst-form button').click();
  await waitTick(paused.tick+3);
  assert.equal((await frame()).control.remaining,0);
  console.log('PASS real run / pause / step / speed / burst');

  paused=await frame();
  const agent=paused.agents.find(a=>a.x<bootstrap.width/2) || paused.agents[0];
  let camera=await page.evaluate(async({w,h})=>{
    const {fitCamera}=await import('/camera.mjs');
    const c=document.querySelector('canvas');return fitCamera(w,h,c.clientWidth,c.clientHeight,16);
  },{w:bootstrap.width,h:bootstrap.height});
  const clickCell=async(x,y)=>{
    if(await page.locator('#inspector').isVisible()) await page.locator('#close-inspector').click();
    await page.mouse.click(box.x+camera.offsetX+(x+.5)*camera.cell,box.y+camera.offsetY+(y+.5)*camera.cell);
  };
  const clickAgent=async(item)=>{
    if(await page.locator('#inspector').isVisible()) await page.locator('#close-inspector').click();
    const [mx,my]=item.micro_position;
    await page.mouse.click(box.x+camera.offsetX+(mx+.5)*camera.cell/3,
      box.y+camera.offsetY+(my+.5)*camera.cell/3);
  };
  const title=()=>page.locator('#inspector [data-title]').innerText();
  await clickCell(agent.x,agent.y);
  await page.waitForFunction(()=>document.querySelector('#inspector [data-title]').textContent==='grass');
  await clickAgent(agent);
  await page.waitForFunction(id=>document.querySelector('#inspector [data-title]').textContent===`gaiano #${id}`,agent.id);
  assert.match(await page.locator('#inspector').innerText(),/orientação[\s\S]*fome[\s\S]*sede[\s\S]*geração[\s\S]*carga/);
  assert.equal(requests.some(p=>p.endsWith('/memory')||p.endsWith('/log')),false);
  assert.equal(await page.locator('#tab-memory').isVisible(),true);
  await page.locator('#tab-memory').focus();
  const [memoryResponse]=await Promise.all([
    page.waitForResponse(r=>r.url().endsWith(`/agent/${agent.id}/memory`)),
    page.keyboard.press('Space'),
  ]);
  const memory=(await memoryResponse.json()).detail;
  await page.waitForFunction(()=>document.querySelector('#history-content .reading-count'));
  assert.equal(await page.locator('#history-content .history-list > li').count(),memory.relations.length);
  assert.equal((await frame()).tick,paused.tick,'space on a tab must not run the simulation');
  const memoryRequests=requests.filter(p=>p.endsWith('/memory')).length;
  await page.locator('#history-content summary').first().click();
  await page.waitForTimeout(450);
  assert.equal(requests.filter(p=>p.endsWith('/memory')).length,memoryRequests);
  assert.equal(await page.locator('#history-content details').first().getAttribute('open'),'');
  const scroll=await page.locator('#history-panel').evaluate(el=>{el.scrollTop=el.scrollHeight;return el.scrollTop;});
  assert.ok(scroll>0,'long memory must scroll independently of the inspector controls');
  assert.equal(await page.evaluate(()=>{
    const button=document.querySelector('#tab-log'),r=button.getBoundingClientRect();
    return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===button;
  }),true,'tabs remain reachable while reading a long memory');
  await page.route('**/agent/*/memory',route=>route.fulfill({status:503,json:{error:'memory unavailable'}}));
  await page.locator('#refresh-inspection').click();
  await page.waitForFunction(()=>document.querySelector('#history-status').textContent.includes('memory unavailable'));
  assert.equal(await page.locator('#history-content .history-list > li').count(),memory.relations.length);
  await page.unroute('**/agent/*/memory');
  await page.locator('#refresh-inspection').click();
  await page.waitForFunction(()=>document.querySelector('#history-status').textContent==='');
  await page.locator('#tab-log').click();
  await page.waitForSelector('#log-source');
  await page.locator('#log-source').selectOption('events');
  assert.ok((await page.locator('#history-content').innerText()).includes('eventos globais'));
  await page.locator('#tab-summary').click();
  assert.equal(await page.locator('#history-panel').isVisible(),false);
  console.log('PASS on-demand memory / evidence / logs / no semantic inference / failed detail retains reading / keyboard safety');
  await page.locator('#selection-candidates [data-layer="terrain"]').click();
  assert.match(await page.locator('#inspector').innerText(),/bloqueio/);
  await clickCell(1,1);
  await page.locator('#selection-candidates [data-layer="terrain"]').click();
  assert.equal(await title(),'water');

  const counts=new Map();
  for(const o of paused.objects){const key=`${o.x},${o.y}`;counts.set(key,[...(counts.get(key)||[]),o]);}
  const stack=[...counts.values()].find(items=>items.length>=2);
  assert.ok(stack,'real scene must include multiple objects in a cell');
  await clickCell(stack[0].x,stack[0].y);
  assert.equal(await page.locator('#selection-candidates [data-layer="object"]').count(),stack.length);
  const target=stack[stack.length-1];
  await page.locator(`#selection-candidates [data-layer="object"][data-id="${target.id}"]`).click();
  assert.equal(await title(),`${target.kind} #${target.id}`);
  await page.locator(`#selection-candidates [data-layer="object"][data-id="${target.id}"]`).evaluate(el=>el.dataset.pollIdentity='stable');
  await page.locator('#inspector-summary [data-fields] dd').first().evaluate(el=>el.dataset.pollIdentity='stable');
  await page.waitForTimeout(450);
  assert.equal(await page.locator(`#selection-candidates [data-layer="object"][data-id="${target.id}"]`).getAttribute('data-poll-identity'),'stable');
  assert.equal(await page.locator('#inspector-summary [data-fields] dd').first().getAttribute('data-poll-identity'),'stable');
  assert.match(await page.locator('#inspector').innerText(),/quantidade/);
  await page.locator('#selection-candidates [data-layer="terrain"]').click();
  for(const object of stack)assert.ok((await page.locator('#inspector').innerText()).includes(`#${object.id}`));
  console.log('PASS real agent / terrain / water / object / multi-object cell inspection');

  await page.locator('#close-inspector').click();
  await page.mouse.move(box.x+200,box.y+200);await page.mouse.down();
  await page.mouse.move(box.x+240,box.y+225,{steps:5});await page.mouse.up();
  camera={...camera,offsetX:camera.offsetX+40,offsetY:camera.offsetY+25};
  await clickAgent(agent);
  assert.equal(await title(),`gaiano #${agent.id}`);
  await page.locator('#close-inspector').click();
  const anchor={x:box.width/2,y:box.height/2};
  await page.mouse.move(box.x+anchor.x,box.y+anchor.y);await page.mouse.wheel(0,-120);
  camera=await page.evaluate(async({camera,anchor})=>(await import('/camera.mjs')).zoomCameraAt(camera,anchor.x,anchor.y,1.2),{camera,anchor});
  await page.waitForTimeout(100);
  await clickAgent(agent);
  assert.equal(await title(),`gaiano #${agent.id}`);
  const scaleBefore=await page.locator('#map-scale').innerText();
  assert.equal(await page.locator('#renderer-select').count(),0);
  assert.equal(await title(),`gaiano #${agent.id}`);
  assert.equal(await page.locator('#map-scale').innerText(),scaleBefore);
  const agentScreen={x:box.x+camera.offsetX+(agent.micro_position[0]+.5)*camera.cell/3,
    y:box.y+camera.offsetY+(agent.micro_position[1]+.5)*camera.cell/3};
  await page.mouse.move(agentScreen.x+3,agentScreen.y+3);await page.mouse.move(agentScreen.x,agentScreen.y);
  await page.waitForFunction(()=>document.querySelector('#world-hover').textContent.includes('[gaiano]'));
  await page.locator('#world-canvas').focus();await page.keyboard.press('r');
  assert.deepEqual(await frame(),paused,'observation/navigation/rendering must not advance or change state');
  console.log('PASS pan / zoom / ascii-only world / unchanged physical frame while observing');

  await page.locator('#follow-agent').click();
  await page.locator('#step-button').click();await waitTick(paused.tick+1);
  const afterStep=await frame(),updated=afterStep.agents.find(a=>a.id===agent.id);
  assert.equal(await title(),`gaiano #${agent.id}`);
  assert.ok((await page.locator('#inspector').innerText()).includes(`${updated.x}, ${updated.y}`));
  await page.route('**/api/frame',route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":"test interruption"}'}));
  await page.waitForFunction(()=>document.querySelector('#connection-label').textContent==='reconectando');
  assert.equal(await title(),`gaiano #${agent.id}`);
  assert.equal(await uiTick(),afterStep.tick);
  await page.unroute('**/api/frame');
  await page.waitForFunction(()=>document.querySelector('#connection-label').textContent==='conectado');
  const beforeBootstrap=requests.filter(p=>p==='/api/bootstrap').length;
  await page.route('**/api/frame',async route=>{
    const data=await (await route.fetch()).json();
    await route.fulfill({json:{...data,worldRevision:'incompatible-test-revision'}});
  },{times:1});
  await page.waitForTimeout(650);
  assert.ok(requests.filter(p=>p==='/api/bootstrap').length>beforeBootstrap);
  assert.equal(await uiTick(),afterStep.tick);
  assert.equal(requests.includes('/api/snapshot'),false);
  assert.deepEqual(failures,[]);
  console.log('PASS inspector follows / connection recovery / revision resync / no legacy snapshot / no JS errors');
} finally {
  await browser?.close();
  lines.close();server.kill('SIGTERM');
}
