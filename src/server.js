import http from 'node:http';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { networkInterfaces } from 'node:os';
import { randomInt, randomUUID } from 'node:crypto';
import { WebSocketServer, WebSocket } from 'ws';
import { CHARACTERS, TIMING, EXECUTION_MS } from '../shared/catalog.js';
import { newFighter, resetRound, canChoose, resolveTurn, roundWinner } from './combat.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.glb': 'model/gltf-binary', '.svg': 'image/svg+xml', '.png': 'image/png' };

export function lanAddresses(port) {
  return Object.values(networkInterfaces()).flat().filter(a => a.family === 'IPv4' && !a.internal).map(a => `http://${a.address}:${port}`);
}

function staticFile(url) {
  let pathname;
  try { pathname = decodeURIComponent(new URL(url, 'http://arena.local').pathname); } catch { return null; }
  if (['/shared/catalog.js', '/shared/presentation.js'].includes(pathname)) return path.join(root, pathname.slice(1));
  const vendor = pathname.startsWith('/vendor/');
  const base = path.join(root, vendor ? 'node_modules/three' : 'public');
  const suffix = vendor ? pathname.slice(8) : (pathname === '/' ? 'index.html' : pathname.slice(1));
  const resolved = path.resolve(base, suffix);
  if (!resolved.startsWith(base + path.sep) || suffix.split('/').some(part => part.startsWith('.'))) return null;
  return resolved;
}

export function createArena({ planMs = TIMING.plan, roundBreakMs = TIMING.roundBreak } = {}) {
  const rooms = new Map();
  const clients = new Map();
  const timers = new Set();
  const server = http.createServer(async (req, res) => {
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'same-origin');
    res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405); res.end(); return; }
    if (req.url === '/api/lan') {
      const port = server.address()?.port;
      res.writeHead(200, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(req.method === 'HEAD' ? '' : JSON.stringify({ urls: lanAddresses(port) }));
      return;
    }
    const filename = staticFile(req.url);
    if (!filename) { res.writeHead(404); res.end('Not found'); return; }
    try {
      const info = await stat(filename);
      if (!info.isFile()) throw new Error('Not a file');
      res.writeHead(200, { 'Content-Type': mime[path.extname(filename)] || 'application/octet-stream', 'Content-Length': info.size, 'Cache-Control': 'no-cache' });
      if (req.method === 'HEAD') res.end();
      else createReadStream(filename).on('error', () => res.destroy()).pipe(res);
    } catch { res.writeHead(404); res.end('Not found'); }
  });
  const wss = new WebSocketServer({ noServer: true, maxPayload: 4096, perMessageDeflate: false });
  const later = (fn, ms) => {
    const timer = setTimeout(() => { timers.delete(timer); fn(); }, ms);
    timers.add(timer);
    return timer;
  };
  const cancel = room => { clearTimeout(room.timer); timers.delete(room.timer); };
  const send = (ws, data) => { if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(data)); };
  const fail = (client, message) => send(client.ws, { type: 'error', message });

  function snapshot(room, id) {
    return {
      code: room.code, host: room.host, stage: room.stage, round: room.round, turn: room.turn,
      deadline: room.deadline, timeline: room.timeline, result: room.result, notice: room.notice,
      players: room.players.map(p => ({ ...p, choice: p.id === id ? p.choice : null })),
    };
  }
  function broadcast(room) {
    for (const p of room.players) {
      const client = clients.get(p.id);
      send(client?.ws, { type: 'state', you: p.id, now: Date.now(), room: snapshot(room, p.id) });
    }
  }
  function startPlanning(room) {
    room.stage = 'plan';
    room.timeline = null;
    room.result = null;
    room.notice = null;
    room.deadline = Date.now() + planMs;
    for (const p of room.players) {
      p.choice = null;
      p.locked = false;
      if (p.bot) {
        const choices = ['strike', 'strike', 'heavy', 'guard', 'special'].filter(a => canChoose(p, a));
        p.choice = choices[randomInt(choices.length)];
        p.locked = true;
      }
    }
    room.timer = later(() => beginExecution(room), planMs);
    broadcast(room);
  }
  function finishExecution(room, outcome) {
    if (!rooms.has(room.code) || room.stage !== 'execute') return;
    for (const after of outcome.after) Object.assign(room.players.find(p => p.id === after.id), after);
    const winner = roundWinner(room.players, room.turn);
    if (winner === undefined) { room.turn++; startPlanning(room); return; }
    if (winner) room.players.find(p => p.id === winner).wins++;
    room.result = { winner, draw: winner === null };
    room.timeline = null;
    room.stage = room.players.some(p => p.wins >= 2) ? 'finished' : 'roundEnd';
    room.deadline = room.stage === 'finished' ? 0 : Date.now() + roundBreakMs;
    if (room.stage === 'roundEnd') room.timer = later(() => {
      if (winner) room.round++;
      room.turn = 1;
      resetRound(room.players);
      startPlanning(room);
    }, roundBreakMs);
    broadcast(room);
  }
  function beginExecution(room) {
    if (room.stage !== 'plan' || room.players.length !== 2) return;
    cancel(room);
    room.stage = 'execute';
    const outcome = resolveTurn(room.players, room.turn);
    const started = Date.now();
    // Damage is applied after the visible timeline, so health bars follow the impact frame.
    room.timeline = { started, events: outcome.events };
    room.deadline = started + EXECUTION_MS;
    room.timer = later(() => finishExecution(room, outcome), EXECUTION_MS);
    broadcast(room);
  }
  function leave(client, notify = true) {
    const room = rooms.get(client.room);
    client.room = null;
    if (!room) { if (notify) send(client.ws, { type: 'left' }); return; }
    cancel(room);
    room.players = room.players.filter(p => p.id !== client.id);
    if (!room.players.some(p => !p.bot)) rooms.delete(room.code);
    else {
      room.host = room.players.find(p => !p.bot).id;
      room.stage = 'lobby';
      room.timeline = null;
      room.result = null;
      room.deadline = 0;
      room.notice = '对手已离开，房间回到准备阶段。';
      room.players.forEach(p => { p.wins = 0; });
      resetRound(room.players);
      broadcast(room);
    }
    if (notify) send(client.ws, { type: 'left' });
  }
  function identity(message) {
    if (typeof message.character !== 'string' || !Object.hasOwn(CHARACTERS, message.character)) throw new Error('请选择有效角色。');
    if (typeof message.name !== 'string') throw new Error('请输入昵称。');
    const name = message.name.normalize('NFKC').replace(/[\p{Cc}\p{Cf}<>]/gu, '').trim().slice(0, 20);
    if (!name) throw new Error('请输入昵称。');
    return { name, character: message.character };
  }
  function handle(client, message) {
    if (!message || typeof message !== 'object' || Array.isArray(message)) throw new Error('无效消息。');
    if (message.type === 'ping') { send(client.ws, { type: 'pong', sent: message.sent, now: Date.now() }); return; }
    if (message.type === 'leave') { leave(client); return; }
    if (message.type === 'create') {
      const profile = identity(message);
      if (rooms.size >= 32) throw new Error('房间已满，请稍后再试。');
      if (Date.now() - client.lastCreate < 1500) throw new Error('创建太快，请稍后再试。');
      client.lastCreate = Date.now();
      leave(client, false);
      let code;
      do { code = Array.from({ length: 6 }, () => 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'[randomInt(32)]).join(''); } while (rooms.has(code));
      const room = { code, host: client.id, players: [newFighter(client.id, profile.name, profile.character)], stage: 'lobby', round: 1, turn: 1, deadline: 0, timeline: null, result: null, notice: null };
      if (message.practice === true) {
        const ids = Object.keys(CHARACTERS).filter(id => id !== profile.character);
        const character = ids[randomInt(ids.length)];
        room.players.push(newFighter(randomUUID(), `${CHARACTERS[character].name} · 陪练`, character, true));
      }
      rooms.set(code, room);
      client.room = code;
      if (message.practice === true) startPlanning(room);
      else broadcast(room);
      return;
    }
    if (message.type === 'join') {
      const profile = identity(message);
      if (typeof message.code !== 'string' || !/^[A-Z2-9]{6}$/.test(message.code.toUpperCase())) throw new Error('请输入 6 位房间码。');
      const room = rooms.get(message.code.toUpperCase());
      if (!room) throw new Error('未找到房间，请确认房间码和主机地址。');
      if (room.players.length >= 2 || room.stage !== 'lobby') throw new Error('房间正在对战或已满。');
      if (client.room === room.code) throw new Error('你已在这个房间中。');
      leave(client, false);
      room.players.push(newFighter(client.id, profile.name, profile.character));
      client.room = room.code;
      room.notice = null;
      broadcast(room);
      return;
    }
    const room = rooms.get(client.room);
    if (!room) throw new Error('请先进入房间。');
    const player = room.players.find(p => p.id === client.id);
    if (message.type === 'start' || message.type === 'rematch') {
      if (room.host !== client.id) throw new Error('请等待房主开始。');
      if (room.players.length !== 2) throw new Error('需要两位玩家。');
      if ((message.type === 'start' && room.stage !== 'lobby') || (message.type === 'rematch' && room.stage !== 'finished')) throw new Error('当前阶段不能开始。');
      cancel(room);
      room.round = room.turn = 1;
      room.players.forEach(p => { p.wins = 0; });
      resetRound(room.players);
      startPlanning(room);
    } else if (message.type === 'choose') {
      if (room.stage !== 'plan' || player.locked) throw new Error('本回合已经锁定。');
      if (!canChoose(player, message.action)) throw new Error('气势不足或招式无效。');
      player.choice = message.action;
      player.locked = true;
      if (room.players.every(p => p.locked)) beginExecution(room);
      else broadcast(room);
    } else throw new Error('不支持的操作。');
  }

  server.on('upgrade', (req, socket, head) => {
    const origin = req.headers.origin;
    let sameOrigin = true;
    try { sameOrigin = !origin || new URL(origin).host === req.headers.host; } catch { sameOrigin = false; }
    const ip = req.socket.remoteAddress;
    const count = [...clients.values()].filter(c => c.ip === ip).length;
    if (req.url !== '/ws' || !sameOrigin || count >= 16 || clients.size >= 128) { socket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n'); return; }
    wss.handleUpgrade(req, socket, head, ws => wss.emit('connection', ws, req));
  });
  wss.on('connection', (ws, req) => {
    const client = { ws, id: randomUUID(), ip: req.socket.remoteAddress, room: null, count: 0, window: Date.now(), lastCreate: 0, alive: true };
    clients.set(client.id, client);
    send(ws, { type: 'hello', id: client.id, now: Date.now() });
    ws.on('pong', () => { client.alive = true; });
    ws.on('error', () => {});
    ws.on('message', (raw, binary) => {
      if (Date.now() - client.window > 1000) { client.window = Date.now(); client.count = 0; }
      if (++client.count > 30) { ws.close(1008, 'Too many messages'); return; }
      try {
        if (binary) throw new Error('仅支持文本消息。');
        handle(client, JSON.parse(raw.toString()));
      } catch (error) { fail(client, error instanceof SyntaxError ? '消息格式错误。' : error.message); }
    });
    ws.on('close', () => { leave(client, false); clients.delete(client.id); });
  });
  const heartbeat = setInterval(() => {
    for (const client of clients.values()) {
      if (!client.alive) { client.ws.terminate(); continue; }
      client.alive = false;
      client.ws.ping();
    }
  }, 15000);
  heartbeat.unref();
  return {
    server, rooms,
    async close() {
      clearInterval(heartbeat);
      timers.forEach(clearTimeout);
      for (const client of clients.values()) client.ws.terminate();
      await new Promise(resolve => wss.close(resolve));
      await new Promise(resolve => server.close(resolve));
    },
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const port = Number(process.env.PORT || 3000);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PORT must be 1–65535');
  const arena = createArena();
  arena.server.on('error', error => { console.error(`无法启动：${error.message}`); process.exitCode = 1; });
  arena.server.listen(port, '0.0.0.0', () => {
    console.log(`All-Star Brawl · http://localhost:${port}`);
    lanAddresses(port).forEach(url => console.log(`局域网加入：${url}`));
  });
  const stop = () => arena.close().then(() => process.exit(0));
  process.once('SIGINT', stop);
  process.once('SIGTERM', stop);
}
