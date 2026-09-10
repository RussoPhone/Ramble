// mount(surface), resize({width,height,ratio}), render(RenderScene,camera,options),
// hitTest({x,y}) -> public records in selection priority, dispose().
// All coordinates passed to hitTest are CSS pixels; world coordinates remain integers.
export function assertRenderer(renderer) {
  for (const method of ['mount','resize','render','hitTest','dispose']) {
    if (typeof renderer[method] !== 'function') throw new TypeError(`Renderer sem ${method}`);
  }
  return renderer;
}
