export function parseTickRate(value) {
  if (typeof value === 'string' && value.trim() === '') throw new RangeError('Ritmo inválido');
  const rate=Number(value);
  if(!Number.isFinite(rate)||rate<.1||rate>100000)throw new RangeError('Ritmo deve ficar entre 0.1 e 100000 ticks/s');
  return rate;
}
