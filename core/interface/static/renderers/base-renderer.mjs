import { visibleBounds, screenToWorld } from '../camera.mjs';
import { candidatesAt, resolveSelection } from '../selection.mjs';
import { cellRecords } from '../scene-model.mjs';

export class BaseRenderer {
  mount(surface) { this.surface=surface; this.ctx=surface.getContext('2d'); }
  resize(viewport) {
    this.viewport=viewport;
    const ratio=viewport.ratio || 1;
    const w=Math.round(viewport.width*ratio),h=Math.round(viewport.height*ratio);
    if(this.surface.width!==w)this.surface.width=w;
    if(this.surface.height!==h)this.surface.height=h;
    this.ctx.setTransform(ratio,0,0,ratio,0,0);
    this.ctx.imageSmoothingEnabled=false;
  }
  agentWorldPoint(agent) {
    const [mx,my]=agent.visual_micro_position || agent.micro_position;
    return {x:(mx+.5)/3,y:(my+.5)/3};
  }
  render(scene,camera,options={}) {
    this.scene=scene; this.camera=camera;
    this.agentHits=[];
    const ctx=this.ctx,v=this.viewport;
    ctx.clearRect(0,0,v.width,v.height);
    ctx.fillStyle=this.background || '#20261f'; ctx.fillRect(0,0,v.width,v.height);
    if(!scene||!camera)return;
    const b=visibleBounds(camera,v,scene.width,scene.height);
    const within=item=>item.x>=b.left&&item.x<=b.right&&item.y>=b.top&&item.y<=b.bottom;
    for(let y=b.top;y<=b.bottom;y++)for(let x=b.left;x<=b.right;x++) {
      for(const item of cellRecords(scene,x,y))if(item.layer==='terrain')this.tile(item,camera);
    }
    if(options.vision?.length){
      ctx.save();
      ctx.fillStyle='rgba(95, 126, 131, 0.24)';
      for(const cell of options.vision){
        const vx=cell[0],vy=cell[1];
        if(vx<b.left||vx>b.right||vy<b.top||vy>b.bottom)continue;
        ctx.fillRect(camera.offsetX+vx*camera.cell,camera.offsetY+vy*camera.cell,camera.cell,camera.cell);
      }
      ctx.restore();
    }
    for(const item of scene.objects.filter(within))this.object(item,camera,
      cellRecords(scene,item.x,item.y).filter(i=>i.layer==='object'));
    const old=new Map((options.previous?.agents || []).map(a=>[a.id,a]));
    for(const agent of scene.agents.filter(within)) {
      const prior=old.get(agent.id),p=options.motionProgress??1;
      // Only interpolate adjacent steps; skipped ticks must not invent paths through obstacles.
      const can=options.previous?.worldRevision===scene.worldRevision && scene.tick===options.previous.tick+1 &&
        prior&&Math.abs(agent.micro_position[0]-prior.micro_position[0])+
          Math.abs(agent.micro_position[1]-prior.micro_position[1])===1;
      const visualMicro=can?prior.micro_position.map((value,index)=>
        value+(agent.micro_position[index]-value)*p):[...agent.micro_position];
      const visual={...agent,visual_micro_position:visualMicro};
      this.agent(visual,camera,options);
      const point=this.agentWorldPoint(visual),unit=camera.cell/3;
      const centers=[point,{x:point.x+agent.orientation[0]/3,y:point.y+agent.orientation[1]/3}];
      this.agentHits.push({agent,centers:centers.map(({x,y})=>({
        x:camera.offsetX+x*camera.cell,y:camera.offsetY+y*camera.cell})),radius:unit*.72});
    }
    const selected=resolveSelection(scene,options.selection);
    if(selected){
      const cells=selected.layer==='agent'?selected.collision_cells:null;
      const left=cells?Math.min(...cells.map(c=>c[0]))/3:selected.x;
      const top=cells?Math.min(...cells.map(c=>c[1]))/3:selected.y;
      const right=cells?(Math.max(...cells.map(c=>c[0]))+1)/3:selected.x+1;
      const bottom=cells?(Math.max(...cells.map(c=>c[1]))+1)/3:selected.y+1;
      const x=Math.round(camera.offsetX+left*camera.cell)+.5,y=Math.round(camera.offsetY+top*camera.cell)+.5;
      const width=Math.round((right-left)*camera.cell)-1,height=Math.round((bottom-top)*camera.cell)-1;
      const arm=Math.max(3,Math.floor(Math.min(width,height)*.25));
      ctx.beginPath();
      for(const [dx,dy,sx,sy] of [[0,0,1,1],[width,0,-1,1],[0,height,1,-1],[width,height,-1,-1]]){
        ctx.moveTo(x+dx+sx*arm,y+dy);ctx.lineTo(x+dx,y+dy);ctx.lineTo(x+dx,y+dy+sy*arm);
      }
      ctx.strokeStyle='#282d25';ctx.lineWidth=3;ctx.stroke();
      ctx.strokeStyle='#c3b597';ctx.lineWidth=1;ctx.stroke();
    }
  }
  hitTest(point) {
    if(!this.scene||!this.camera)return[];
    // Pick a moving glyph where it is actually drawn, but return authoritative
    // records and the candidates of its logical cell, never interpolated state.
    const visible=(this.agentHits||[]).map(hit=>({...hit,distance:Math.min(...hit.centers.map(center=>
      Math.hypot(point.x-center.x,point.y-center.y)))}))
      .filter(hit=>hit.distance<=hit.radius).sort((a,b)=>a.distance-b.distance)[0];
    if(visible)return candidatesAt(this.scene,visible.agent.x,visible.agent.y,
      {layer:'agent',id:visible.agent.id});
    const world=screenToWorld(this.camera,point.x,point.y);
    return candidatesAt(this.scene,Math.floor(world.x),Math.floor(world.y),{layer:'terrain'});
  }
  dispose(){this.scene=null;this.surface=null;this.ctx=null;this.camera=null;this.agentHits=[];}
}
