export class ObserverTransport {
  async request(path, options={}) {
    const controller = new AbortController();
    const timer = setTimeout(()=>controller.abort(),8000);
    try {
      const response = await fetch(path,{cache:'no-store',...options,signal:controller.signal});
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || `HTTP ${response.status}`);
      return body;
    } finally { clearTimeout(timer); }
  }
  bootstrap() { return this.request('/api/bootstrap'); }
  frame() { return this.request('/api/frame'); }
  control(command,value) {
    return this.request('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({command,...(value===undefined?{}:{value})})});
  }
  detail(item, section='summary') {
    const path = item.layer==='terrain' ? `cell/${item.x}/${item.y}` : `${item.layer}/${item.id}`;
    const suffix=item.layer==='agent'&&['memory','log'].includes(section)?`/${section}`:'';
    return this.request(`/api/selection/${path}${suffix}`);
  }
}
