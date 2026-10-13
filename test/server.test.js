import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { WebSocket } from 'ws';
import { createArena } from '../src/server.js';

async function arena(t, options) {
  const app = createArena(options);
  app.server.listen(0, '127.0.0.1');
  await once(app.server, 'listening');
  t.after(() => app.close());
  return { ...app, url: `http://127.0.0.1:${app.server.address().port}` };
}
async function client(url) {
  const ws = new WebSocket(url.replace('http:', 'ws:') + '/ws');
  const messages = [], listeners = new Set();
  ws.on('message', raw => {
    const message = JSON.parse(raw);
    messages.push(message);
    for (const listener of listeners) listener(message);
  });
  function wait(predicate, timeout = 6000) {
    const existing = messages.find(predicate);
    if (existing) { messages.splice(messages.indexOf(existing), 1); return Promise.resolve(existing); }
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { listeners.delete(onMessage); reject(new Error('Timed out waiting for server')); }, timeout);
      function onMessage(message) {
        if (!predicate(message)) return;
        clearTimeout(timer); listeners.delete(onMessage); messages.splice(messages.indexOf(message), 1); resolve(message);
      }
      listeners.add(onMessage);
    });
  }
  const hello = await wait(m => m.type === 'hello');
  return { ws, id: hello.id, wait, send: message => ws.send(JSON.stringify(message)) };
}
const state = stage => m => m.type === 'state' && m.room.stage === stage;

test('two clients create, join, hide choices, resolve a turn and clean up on disconnect', async t => {
  const app = await arena(t, { planMs: 12000 });
  const a = await client(app.url), b = await client(app.url);
  a.send({ type: 'create', name: 'Host', character: 'ikun' });
  const first = await a.wait(state('lobby'));
  b.send({ type: 'join', code: first.room.code, name: 'Guest', character: 'wang' });
  await b.wait(state('lobby'));
  b.send({ type: 'start' });
  assert.match((await b.wait(m => m.type === 'error')).message, /房主/);
  a.send({ type: 'start' });
  await a.wait(state('plan')); await b.wait(state('plan'));
  a.send({ type: 'choose', action: 'heavy' });
  const secret = await b.wait(m => state('plan')(m) && m.room.players.find(p => p.id === a.id).locked);
  assert.equal(secret.room.players.find(p => p.id === a.id).choice, null);
  a.send({ type: 'choose', action: 'strike' });
  assert.match((await a.wait(m => m.type === 'error')).message, /锁定/);
  b.send({ type: 'choose', action: 'guard' });
  const execution = await b.wait(state('execute'));
  assert.equal(execution.room.timeline.events[0].damage, 24);
  const next = await a.wait(m => state('plan')(m) && m.room.turn === 2);
  assert.equal(next.room.players.find(p => p.id === b.id).hp, 116 - 24);
  assert.equal(next.room.players.find(p => p.id === a.id).energy, 0);
  b.ws.close();
  const lobby = await a.wait(m => state('lobby')(m) && m.room.players.length === 1 && m.room.notice);
  assert.equal(lobby.room.host, a.id);
  a.send({ type: 'leave' }); await a.wait(m => m.type === 'left');
  assert.equal(app.rooms.size, 0);
});

test('practice and timeout work without another browser', async t => {
  const app = await arena(t, { planMs: 80 });
  const a = await client(app.url);
  a.send({ type: 'create', name: '练习', character: 'lubu', practice: true });
  const plan = await a.wait(state('plan'));
  assert.equal(plan.room.players[1].bot, true);
  assert.equal(plan.room.players[1].choice, null);
  const execute = await a.wait(state('execute'));
  assert.equal(execute.room.timeline.events.find(e => e.actor === a.id).action, 'guard');
  a.send({ type: 'leave' }); await a.wait(m => m.type === 'left');
  assert.equal(app.rooms.size, 0);
});

test('reject malformed input, full rooms, forged damage and inaccessible server files', async t => {
  const app = await arena(t);
  const a = await client(app.url), b = await client(app.url), c = await client(app.url);
  a.ws.send('{'); assert.match((await a.wait(m => m.type === 'error')).message, /格式/);
  a.send({ type: 'create', name: 'x', character: '__proto__' }); await a.wait(m => m.type === 'error');
  a.send({ type: 'create', name: '<Host>', character: 'ikun' });
  const lobby = await a.wait(state('lobby'));
  assert.equal(lobby.room.players[0].name, 'Host');
  b.send({ type: 'join', name: 'B', character: 'wang', code: lobby.room.code }); await b.wait(state('lobby'));
  c.send({ type: 'join', name: 'C', character: 'lubu', code: lobby.room.code });
  assert.match((await c.wait(m => m.type === 'error')).message, /已满/);
  a.send({ type: 'damage', amount: 9999 }); await a.wait(m => m.type === 'error');
  for (const filename of ['/src/server.js', '/art/all-stars.blend', '/.env', '/assets/%2e%2e/%2e%2e/src/server.js']) {
    const missing = await fetch(app.url + filename);
    assert.equal(missing.status, 404, filename);
    await missing.text();
  }
  const response = await fetch(app.url);
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-security-policy'), /frame-ancestors 'none'/);
  await response.text();
  const asset = await fetch(app.url + '/assets/ikun.glb');
  assert.equal(asset.headers.get('content-type'), 'model/gltf-binary');
  await asset.arrayBuffer();
  const module = await fetch(app.url + '/vendor/build/three.module.js');
  assert.equal(module.status, 200);
  await module.text();
  const presentation = await fetch(app.url + '/shared/presentation.js');
  assert.equal(presentation.status, 200);
  assert.match(await presentation.text(), /export function presentationTime/);
});

test('cross-origin WebSocket attempts are refused', async t => {
  const app = await arena(t);
  const ws = new WebSocket(app.url.replace('http:', 'ws:') + '/ws', { origin: 'http://unrelated.example' });
  const [error] = await once(ws, 'error');
  assert.match(error.message, /403/);
});

test('draws replay the same round, two wins finish the match, and only the host can rematch', async t => {
  const app = await arena(t, { planMs: 12000, roundBreakMs: 20 });
  const a = await client(app.url), b = await client(app.url);
  a.send({ type: 'create', name: 'A', character: 'ikun' });
  const lobby = await a.wait(state('lobby'));
  b.send({ type: 'join', name: 'B', character: 'lubu', code: lobby.room.code });
  await b.wait(state('lobby'));
  a.send({ type: 'start' }); await a.wait(state('plan')); await b.wait(state('plan'));
  // Server-side fixture places the duel at a double-KO boundary without trusting client damage.
  const liveRoom = app.rooms.get(lobby.room.code);
  liveRoom.players.forEach(p => { p.hp = 1; });
  a.send({ type: 'choose', action: 'strike' }); b.send({ type: 'choose', action: 'strike' });
  const draw = await a.wait(state('roundEnd'));
  assert.equal(draw.room.result.draw, true);
  const replay = await a.wait(m => state('plan')(m) && m.room.players.every(p => p.hp > 1));
  assert.equal(replay.room.round, 1);
  assert.deepEqual(replay.room.players.map(p => p.wins), [0, 0]);
  liveRoom.players[0].wins = 1;
  liveRoom.players[1].hp = 1;
  a.send({ type: 'choose', action: 'strike' }); b.send({ type: 'choose', action: 'guard' });
  const finished = await a.wait(state('finished'));
  assert.equal(finished.room.result.winner, a.id);
  assert.equal(finished.room.players[0].wins, 2);
  b.send({ type: 'rematch' }); assert.match((await b.wait(m => m.type === 'error')).message, /房主/);
  a.send({ type: 'rematch' });
  const rematch = await a.wait(m => state('plan')(m) && m.room.players.every(p => p.hp > 1 && p.wins === 0));
  assert.equal(rematch.room.round, 1);
  assert.equal(rematch.room.turn, 1);
  assert.deepEqual(rematch.room.players.map(p => p.energy), [1, 1]);
});
