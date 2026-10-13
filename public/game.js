import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone } from 'three/addons/utils/SkeletonUtils.js';
import { CHARACTERS, ACTIONS, TIMING } from '/shared/catalog.js';

const $ = id => document.getElementById(id);
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const canvas = $('arena');
let selected = 'ikun', choice = 'strike', room = null, you = null, connected = false;
let clockOffset = 0, socket, toastTimer, soundEnabled = false, audio;
let previewActor, opponent, opponentId, presentation = 'home', previewAngle = -.18;
let yaw = 0, pitch = 0, drag = null, viewCharacter = null, lastTimeline = null;
let shake = 0, flash = 0, freezeUntil = 0, weaponMotion = null, shownHp = new Map();
const startedEvents = new Set(), hitEvents = new Set(), logLines = [], keys = new Set();
const models = new Map();
const actors = new Set();
const now = () => Date.now() + clockOffset;

function toast(message) {
  $('toast').textContent = message;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4200);
}
function send(message) {
  if (!connected || socket.readyState !== WebSocket.OPEN) { toast('正在连接主机，请稍后再试。'); return; }
  socket.send(JSON.stringify(message));
}
function profile() {
  const name = $('nickname').value.trim();
  if (!name) { $('nickname').reportValidity(); return null; }
  localStorage.setItem('asb-name', name);
  return { name, character: selected };
}
function create(practice = false) {
  const identity = profile();
  if (identity) { unlock(); send({ type: 'create', ...identity, practice }); }
}

function createRenderer() {
  try { return new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' }); }
  catch (error) {
    $('model-status').textContent = '需要支持 WebGL 2 的浏览器';
    toast('无法启动三维画面，请开启浏览器硬件加速并刷新。');
    throw error;
  }
}
const renderer = createRenderer();
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.3;
renderer.setClearColor(0x10131c);
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x10131c, .035);
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, .05, 90);
const previewCamera = new THREE.PerspectiveCamera(34, 1, .05, 50);
const hemi = new THREE.HemisphereLight(0xc9d2ff, 0x27223a, 2.4);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffefdc, 3.6);
key.position.set(3, 8, 5);
key.castShadow = true;
key.shadow.mapSize.set(1024, 1024);
key.shadow.camera.left = key.shadow.camera.bottom = -9;
key.shadow.camera.right = key.shadow.camera.top = 9;
key.shadow.normalBias = .035;
scene.add(key);
const rim = new THREE.DirectionalLight(0x9686ff, 3);
rim.position.set(-4, 4, -4);
scene.add(rim);
const fill = new THREE.PointLight(0xc5ff74, 24, 20, 2);
fill.position.set(2, 2.8, -1);
scene.add(fill);

function mesh(geometry, color, metalness = 0, roughness = .6) {
  return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, metalness, roughness }));
}
const arena = new THREE.Group();
const ground = mesh(new THREE.CylinderGeometry(8.5, 8.8, .3, 80), 0x202635, .4, .65);
ground.position.y = -.2;
ground.receiveShadow = true;
arena.add(ground);
for (const radius of [2.3, 5.8, 8]) {
  const ring = mesh(new THREE.TorusGeometry(radius, radius === 8 ? .032 : .016, 8, 96), radius === 8 ? 0xa89dff : 0x535c72, .5);
  ring.rotation.x = Math.PI / 2;
  ring.position.y = -.03;
  arena.add(ring);
}
const railMaterial = new THREE.MeshStandardMaterial({ color: 0xa89dff, emissive: 0x504171, emissiveIntensity: 1.4 });
for (let i = 0; i < 12; i++) {
  const angle = i * Math.PI / 6;
  const post = mesh(new THREE.CylinderGeometry(.035, .04, 1.1, 8), 0x40475a, .8);
  post.position.set(Math.sin(angle) * 8, .5, Math.cos(angle) * 8);
  arena.add(post);
}
for (const y of [.55, .98]) {
  const rope = new THREE.Mesh(new THREE.TorusGeometry(8, .026, 8, 96), railMaterial);
  rope.rotation.x = Math.PI / 2;
  rope.position.y = y;
  arena.add(rope);
}
for (let i = 0; i < 5; i++) {
  const plinth = mesh(new THREE.BoxGeometry(1.5, 3 + i % 2, .55), 0x171c29, .6);
  plinth.position.set((i - 2) * 4, .9, -13);
  arena.add(plinth);
  const strip = mesh(new THREE.BoxGeometry(.045, 2.3, .03), i % 2 ? 0x6edbc9 : 0xa89dff);
  strip.material.emissive.copy(strip.material.color);
  strip.material.emissiveIntensity = 1.2;
  strip.position.copy(plinth.position).add(new THREE.Vector3(.58, .1, .3));
  arena.add(strip);
}
scene.add(arena);
const podium = mesh(new THREE.CylinderGeometry(1.12, 1.25, .18, 64), 0x303747, .5, .45);
podium.position.y = .02;
podium.receiveShadow = true;
scene.add(podium);
const podiumRing = mesh(new THREE.TorusGeometry(1.14, .013, 8, 96), 0xa89dff);
podiumRing.rotation.x = Math.PI / 2;
podiumRing.position.y = .11;
podiumRing.material.emissive.set(0xa89dff);
podiumRing.material.emissiveIntensity = .7;
scene.add(podiumRing);

const viewmodel = new THREE.Group();
camera.add(viewmodel);
scene.add(camera);
const hands = [];
for (const side of [-1, 1]) {
  const group = new THREE.Group();
  const sleeve = mesh(new THREE.CapsuleGeometry(.077, .26, 6, 12), 0x29253d);
  sleeve.rotation.x = Math.PI / 2;
  sleeve.position.z = .13;
  const fist = mesh(new THREE.SphereGeometry(.09, 16, 12), 0xd39870);
  fist.scale.set(1, .83, 1.25);
  group.add(sleeve, fist);
  group.position.set(side * .48, -.32, -.90);
  group.rotation.z = side * -.28;
  viewmodel.add(group);
  hands.push(group);
}
let weapon;
function setViewmodel(character) {
  if (viewCharacter === character) return;
  viewCharacter = character;
  if (weapon) {
    hands[1].remove(weapon);
    weapon.traverse(obj => { if (obj.isMesh) { obj.geometry.dispose(); obj.material.dispose(); } });
  }
  weapon = new THREE.Group();
  if (character === 'ikun') {
    const ball = mesh(new THREE.SphereGeometry(.135, 24, 16), 0xd8621a, .05, .65);
    weapon.add(ball);
    for (let i = 0; i < 3; i++) {
      const seam = mesh(new THREE.TorusGeometry(.136, .003, 4, 48), 0x211622);
      if (i === 1) seam.rotation.x = Math.PI / 2;
      if (i === 2) seam.rotation.y = Math.PI / 2;
      weapon.add(seam);
    }
    weapon.position.set(.04, .07, -.04);
  } else if (character === 'wang') {
    const handle = mesh(new THREE.CylinderGeometry(.008, .008, .32, 8), 0xb99b5e);
    weapon.add(handle);
    for (let i = 0; i < 7; i++) {
      const feather = mesh(new THREE.SphereGeometry(1, 12, 8), 0xf0e8d2);
      feather.scale.set(.032, .14, .012);
      feather.rotation.z = (i - 3) * -.15;
      feather.position.set((i - 3) * .025, .19, 0);
      weapon.add(feather);
    }
    weapon.position.set(.02, .03, -.07);
  } else {
    const shaft = mesh(new THREE.CylinderGeometry(.012, .014, .85, 8), 0x462430, .6);
    const blade = mesh(new THREE.ConeGeometry(.055, .21, 4), 0xc0cbd9, .9, .25);
    blade.position.y = .50;
    const crescent = mesh(new THREE.TorusGeometry(.084, .018, 6, 16, Math.PI), 0xc0cbd9, .8, .3);
    crescent.position.set(-.03, .36, 0);
    weapon.add(shaft, blade, crescent);
    weapon.rotation.z = -.15;
    weapon.position.set(.05, .1, -.02);
  }
  hands[1].add(weapon);
  for (const hand of hands) hand.children[0].material.color.set(character === 'wang' ? 0x0c6654 : character === 'lubu' ? 0x8c2732 : 0x29253d);
}

function actor(character) {
  const gltf = models.get(character);
  if (!gltf) return null;
  const model = clone(gltf.scene);
  model.traverse(obj => { if (obj.isMesh) { obj.castShadow = true; obj.receiveShadow = true; } });
  const group = new THREE.Group();
  group.add(model);
  scene.add(group);
  const mixer = new THREE.AnimationMixer(model);
  const clips = new Map(gltf.animations.map(clip => [clip.name.toLowerCase(), clip]));
  const instance = { group, mixer, clips, active: null, character };
  mixer.addEventListener('finished', () => play(instance, 'idle'));
  actors.add(instance);
  play(instance, 'idle');
  return instance;
}
function removeActor(instance) {
  if (!instance) return;
  scene.remove(instance.group);
  instance.mixer.stopAllAction();
  instance.mixer.uncacheRoot(instance.group.children[0]);
  actors.delete(instance);
}
function play(instance, name, duration) {
  if (!instance) return;
  const clip = instance.clips.get(name) || [...instance.clips.entries()].find(([key]) => key.endsWith(name))?.[1];
  if (!clip) return;
  const next = instance.mixer.clipAction(clip);
  if (instance.active === next && name === 'idle') return;
  next.reset().setEffectiveWeight(1).setEffectiveTimeScale(1);
  next.setLoop(['idle', 'victory'].includes(name) ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
  next.clampWhenFinished = !['idle', 'victory'].includes(name);
  if (duration) next.setDuration(duration);
  if (instance.active && instance.active !== next) next.crossFadeFrom(instance.active, .12, false);
  next.play();
  instance.active = next;
}
function updatePreview() {
  if (!models.has(selected)) return;
  removeActor(previewActor);
  previewActor = actor(selected);
  previewActor.group.position.set(0, .12, 0);
  previewActor.group.rotation.y = previewAngle;
  podiumRing.material.color.set(CHARACTERS[selected].color);
  podiumRing.material.emissive.set(CHARACTERS[selected].color);
}
function selectCharacter(character) {
  selected = character;
  document.documentElement.style.setProperty('--accent', CHARACTERS[character].color);
  document.querySelectorAll('.character-card').forEach(button => {
    button.classList.toggle('selected', button.dataset.character === character);
    button.setAttribute('aria-pressed', String(button.dataset.character === character));
  });
  $('special-name').textContent = CHARACTERS[character].special;
  $('character-description').textContent = CHARACTERS[character].description;
  updatePreview();
}

function connect() {
  socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
  socket.addEventListener('open', () => {
    connected = true;
    $('network').textContent = '局域网就绪';
    $('network').classList.add('online');
  });
  socket.addEventListener('message', ({ data }) => {
    const message = JSON.parse(data);
    if (message.type === 'hello') { you = message.id; clockOffset = message.now - Date.now(); }
    else if (message.type === 'state') { you = message.you; receiveRoom(message.room); }
    else if (message.type === 'left') { room = null; receiveRoom(null); }
    else if (message.type === 'error') toast(message.message);
    else if (message.type === 'pong') {
      const rtt = Date.now() - message.sent;
      clockOffset = message.now + rtt / 2 - Date.now();
      $('latency').textContent = `${rtt} ms · LAN`;
    }
  });
  socket.addEventListener('close', () => {
    connected = false;
    $('network').textContent = '连接断开';
    $('network').classList.remove('online');
    if (room) { toast('与主机断开连接，当前对战已结束。'); room = null; receiveRoom(null); }
    setTimeout(connect, 2500);
  });
  socket.addEventListener('error', () => {});
}

function visible(id, value) { $(id).hidden = !value; }
function receiveRoom(next) {
  const previous = room;
  room = next;
  presentation = !room ? 'home' : room.stage === 'lobby' ? 'lobby' : 'battle';
  visible('home', presentation === 'home');
  visible('home-footer', presentation === 'home');
  visible('lobby', presentation === 'lobby');
  visible('hud', presentation === 'battle');
  visible('result', room && ['roundEnd', 'finished'].includes(room.stage));
  if (presentation !== 'battle') unlock();
  if (!room) {
    removeActor(opponent); opponent = null; opponentId = null;
    if (previewActor) previewActor.group.visible = true;
    shownHp.clear(); logLines.length = 0;
    yaw = pitch = 0;
    return;
  }
  if (presentation === 'lobby') {
    $('lobby-code').textContent = room.code;
    const list = $('lobby-players'); list.replaceChildren();
    room.players.forEach(p => {
      const slot = document.createElement('div'); slot.className = 'player-slot';
      const name = document.createElement('strong'); name.textContent = p.name;
      const description = document.createElement('span'); description.textContent = `${CHARACTERS[p.character].name}${p.id === room.host ? ' · 房主' : ''}`;
      slot.append(name, description); list.append(slot);
    });
    const ready = room.players.length === 2;
    $('start').disabled = !ready || room.host !== you;
    $('start').textContent = !ready ? '等待对手加入' : room.host === you ? '开始对战 →' : '等待房主开始';
    $('lobby-note').textContent = room.notice || (ready ? '双方入场，三局两胜。' : '等待对手加入…');
    selectCharacter(room.players.find(p => p.id === you).character);
    if (opponent) { removeActor(opponent); opponent = null; opponentId = null; }
    return;
  }
  const self = room.players.find(p => p.id === you);
  const other = room.players.find(p => p.id !== you);
  if (!self || !other) return;
  if (previewActor) previewActor.group.visible = false;
  if (!opponent || opponentId !== other.id || opponent.character !== other.character) {
    removeActor(opponent);
    opponent = actor(other.character);
    opponentId = other.id;
    if (opponent) opponent.group.position.set(0, 0, -1.8);
    yaw = pitch = 0;
  }
  setViewmodel(self.character);
  $('self-name').textContent = `${self.name} · ${CHARACTERS[self.character].name}`;
  $('enemy-name').textContent = `${other.name} · ${CHARACTERS[other.character].name}`;
  $('self-score').textContent = `${'●'.repeat(self.wins)}${'○'.repeat(2 - self.wins)}`;
  $('enemy-score').textContent = `${'●'.repeat(other.wins)}${'○'.repeat(2 - other.wins)}`;
  $('energy').textContent = `气势 ${'◆'.repeat(self.energy)}${'◇'.repeat(3 - self.energy)}`;
  $('enemy-ready').textContent = other.locked ? '招式已锁定' : '正在思考';
  $('round-number').textContent = `ROUND ${String(room.round).padStart(2, '0')} · 三局两胜`;
  $('turn-number').textContent = `TURN ${String(room.turn).padStart(2, '0')}`;
  for (const p of room.players) shownHp.set(p.id, p.hp);
  if (room.stage === 'plan') {
    if (!previous || previous.stage !== 'plan' || previous.turn !== room.turn || previous.round !== room.round) {
      choice = ACTIONS[choice].cost <= self.energy ? choice : 'strike';
      weaponMotion = null; lastTimeline = null;
      if (opponent) { opponent.group.position.set(0, 0, -1.8); play(opponent, 'idle'); }
    }
    $('phase').textContent = self.locked ? '等待对手' : '选择招式';
    $('turn-hint').textContent = self.locked ? '招式已锁定，等待双方亮招。' : '读懂对手，锁定你的回合。';
  } else if (room.stage === 'execute') {
    $('phase').textContent = '出招！';
    $('turn-hint').textContent = '前摇 · 命中 · 收招';
    const identity = `${room.code}:${room.round}:${room.turn}:${room.timeline.started}`;
    if (lastTimeline !== identity) { startedEvents.clear(); hitEvents.clear(); lastTimeline = identity; }
  } else {
    unlock();
    $('countdown').textContent = '—';
    $('turn-hint').textContent = room.stage === 'finished' ? '对战结束，可以再战一场。' : '本局结束，准备下一局。';
    const won = room.result.winner === you;
    $('phase').textContent = room.stage === 'finished' ? '对战结束' : '本局结束';
    $('result-kicker').textContent = room.stage === 'finished' ? 'MATCH COMPLETE' : 'ROUND COMPLETE';
    $('result-title').textContent = room.result.draw ? '势均力敌。' : won ? '你的主场。' : '再来一局。';
    $('result-title').style.color = won ? '#c5ff74' : '#f2f1eb';
    $('result-detail').textContent = room.stage === 'finished' ? `${won ? '你' : other.name}赢下了这场三局两胜的对战。` : room.result.draw ? '这一局平手，下一局重新开始。' : `比分 ${self.wins} : ${other.wins} · 下一局即将开始。`;
    $('rematch').hidden = room.stage !== 'finished';
    $('rematch').disabled = room.host !== you;
    $('rematch').textContent = room.host === you ? '再战一场 →' : '等待房主再战';
    if (!won && !room.result.draw) play(opponent, 'victory');
  }
  renderActions(); updateHealth();
}
function updateHealth() {
  if (!room || room.players.length !== 2) return;
  for (const p of room.players) {
    const prefix = p.id === you ? 'self' : 'enemy';
    const hp = shownHp.get(p.id) ?? p.hp;
    const max = CHARACTERS[p.character].hp;
    $(`${prefix}-hp`).textContent = `${hp} / ${max} HP`;
    $(`${prefix}-health`).style.width = `${hp / max * 100}%`;
  }
}
function renderActions() {
  const self = room?.players.find(p => p.id === you);
  const target = $('actions'); target.replaceChildren();
  for (const [id, action] of Object.entries(ACTIONS)) {
    const button = document.createElement('button');
    button.className = `action${choice === id ? ' selected' : ''}`;
    button.dataset.action = id;
    button.setAttribute('aria-pressed', String(choice === id));
    button.setAttribute('aria-label', `${action.name}，${action.detail}`);
    button.title = id === 'special' && self ? CHARACTERS[self.character].special : action.detail;
    button.disabled = room?.stage !== 'plan' || self?.locked || action.cost > (self?.energy ?? 0);
    const key = document.createElement('span'); key.className = 'key'; key.textContent = action.key;
    const cost = document.createElement('span'); cost.className = 'cost'; cost.textContent = action.cost ? `${action.cost} ◆` : '+1 ◆';
    const title = document.createElement('strong'); title.textContent = action.name;
    const label = document.createElement('span'); label.className = 'action-label'; label.textContent = id === 'special' && self ? CHARACTERS[self.character].special : action.label;
    button.append(key, cost, title, label);
    button.addEventListener('click', () => selectAction(id)); target.append(button);
  }
  $('commit').disabled = room?.stage !== 'plan' || !self || self.locked;
  $('commit').textContent = self?.locked ? '已经锁定 ✓' : '锁定招式 →';
}
function selectAction(action) {
  const self = room?.players.find(p => p.id === you);
  if (!self || self.locked || room.stage !== 'plan' || ACTIONS[action].cost > self.energy) return;
  choice = action; renderActions(); tone(320, .06, 'sine', .03);
}
function commit() {
  const self = room?.players.find(p => p.id === you);
  if (room?.stage === 'plan' && !self.locked) send({ type: 'choose', action: choice });
}

function tone(frequency, duration, type = 'sine', volume = .05, end = frequency) {
  if (!soundEnabled) return;
  audio ||= new (window.AudioContext || window.webkitAudioContext)();
  if (audio.state === 'suspended') audio.resume();
  const osc = audio.createOscillator(), gain = audio.createGain();
  osc.type = type; osc.frequency.setValueAtTime(frequency, audio.currentTime);
  osc.frequency.exponentialRampToValueAtTime(Math.max(20, end), audio.currentTime + duration);
  gain.gain.setValueAtTime(volume, audio.currentTime);
  gain.gain.exponentialRampToValueAtTime(.001, audio.currentTime + duration);
  osc.connect(gain).connect(audio.destination); osc.start(); osc.stop(audio.currentTime + duration);
}
function impact(event) {
  if (event.damage <= 0) return;
  const localHit = event.target === you;
  shownHp.set(event.target, Math.max(0, (shownHp.get(event.target) ?? 0) - event.damage));
  updateHealth();
  if (!reducedMotion) {
    shake = localHit ? .10 : .055;
    freezeUntil = performance.now() + 65;
    flash = localHit ? .30 : .06;
  }
  if (!localHit && opponent) play(opponent, 'hurt');
  const label = $('impact-label');
  label.textContent = `${event.blocked ? '格挡 · ' : event.action === 'special' ? '明星时刻 · ' : ''}−${event.damage}`;
  label.className = `impact-label show${localHit ? ' hurt' : ''}`;
  setTimeout(() => label.classList.remove('show'), 650);
  const actorName = room.players.find(p => p.id === event.actor).name;
  logLines.unshift(`${actorName} · ${event.title}${event.blocked ? '（格挡）' : ''} −${event.damage}`);
  logLines.length = Math.min(logLines.length, 4);
  const log = $('battle-log'); log.replaceChildren();
  logLines.forEach(line => { const div = document.createElement('div'); div.textContent = line; log.append(div); });
  tone(event.blocked ? 540 : 150, .15, 'triangle', .1, event.blocked ? 170 : 40);
  if (event.action === 'special') tone(75, .3, 'sawtooth', .035, 28);
  spawnSparks(localHit ? new THREE.Vector3(0, 1.4, 2.5) : new THREE.Vector3(0, 1.4, -.8), event.blocked ? 0x6edbc9 : 0xc5ff74);
}
const sparkGeometry = new THREE.SphereGeometry(.025, 4, 3);
const sparks = [];
function spawnSparks(position, color) {
  if (reducedMotion) return;
  for (let i = 0; i < 12; i++) {
    const spark = new THREE.Mesh(sparkGeometry, new THREE.MeshBasicMaterial({ color, transparent: true }));
    spark.position.copy(position);
    const velocity = new THREE.Vector3((Math.random() - .5) * 3, Math.random() * 2 + .4, (Math.random() - .5) * 2);
    scene.add(spark); sparks.push({ spark, velocity, life: .5 });
  }
}

function timeline() {
  if (room?.stage !== 'execute' || !room.timeline) return;
  const elapsed = now() - room.timeline.started;
  room.timeline.events.forEach((event, index) => {
    if (elapsed >= event.start && !startedEvents.has(index)) {
      startedEvents.add(index);
      if (event.actor === you) weaponMotion = { started: room.timeline.started + event.start, action: event.action };
      else if (opponent) play(opponent, event.action === 'strike' ? 'attack' : event.action, TIMING.slot / 1000);
      if (event.action !== 'guard') tone(220, .16, 'sine', .02, 360);
    }
    if (elapsed >= event.hit && !hitEvents.has(index)) { hitEvents.add(index); impact(event); }
  });
  if (opponent) {
    const attack = room.timeline.events.find(e => e.actor !== you && e.action !== 'guard');
    let lunge = 0;
    if (attack) {
      const t = (elapsed - attack.start) / TIMING.slot;
      if (t >= 0 && t <= 1) lunge = Math.exp(-(((t - .42) / .19) ** 2)) * (attack.action === 'special' ? 2.4 : 1.9);
    }
    opponent.group.position.z = -1.8 + lunge;
  }
}
function animateHands(dt, time) {
  let drive = 0, ready = 0, guard = 0;
  if (weaponMotion) {
    const t = (now() - weaponMotion.started) / TIMING.slot;
    if (t > 1) weaponMotion = null;
    else if (t >= 0) {
      drive = Math.exp(-(((t - .42) / .13) ** 2));
      ready = Math.exp(-(((t - .18) / .10) ** 2));
      if (weaponMotion.action === 'guard') { guard = Math.sin(t * Math.PI); drive = ready = 0; }
    }
  }
  hands.forEach((hand, index) => {
    const sign = index === 0 ? -1 : 1;
    hand.position.x = sign * .48 - sign * guard * .24;
    hand.position.y = -.32 + (reducedMotion ? 0 : Math.sin(time * 1.8 + index) * .009) + guard * .17 + (index === 1 ? ready * -.07 + drive * .05 : 0);
    hand.position.z = -.90 + (index === 1 ? ready * .15 - drive * .37 : -drive * .08) - guard * .03;
    hand.rotation.x = index === 1 ? drive * -.4 + ready * .2 : 0;
    hand.rotation.z = sign * -.28 - sign * guard * .7;
  });
}

function unlock() { if (document.pointerLockElement) document.exitPointerLock(); }
function look(dx, dy) {
  if (presentation !== 'battle') { previewAngle += dx * .006; return; }
  yaw = THREE.MathUtils.clamp(yaw - dx * .0025, -.9, .9);
  pitch = THREE.MathUtils.clamp(pitch - dy * .0025, -.5, .5);
}
canvas.addEventListener('pointerdown', event => { drag = { x: event.clientX, y: event.clientY }; canvas.setPointerCapture(event.pointerId); });
canvas.addEventListener('pointermove', event => {
  if (document.pointerLockElement === canvas) look(event.movementX, event.movementY);
  else if (drag) { look(event.clientX - drag.x, event.clientY - drag.y); drag = { x: event.clientX, y: event.clientY }; }
});
canvas.addEventListener('pointerup', () => { drag = null; });
canvas.addEventListener('pointercancel', () => { drag = null; });
document.addEventListener('mousemove', event => { if (document.pointerLockElement === canvas && event.target !== canvas) look(event.movementX, event.movementY); });
$('focus').addEventListener('click', async () => {
  try {
    if (!canvas.requestPointerLock) throw new Error('Unsupported');
    await canvas.requestPointerLock();
  } catch { toast('当前浏览器无法锁定鼠标，可以拖动场景或用方向键看向四周。'); }
});
document.addEventListener('pointerlockchange', () => { $('focus').textContent = document.pointerLockElement ? 'Esc 释放' : '锁定视角'; });
window.addEventListener('keydown', event => {
  if (/^(INPUT|TEXTAREA)$/.test(event.target.tagName) || $('help-dialog').open) return;
  if (presentation === 'battle') {
    if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Enter', '1', '2', '3', '4'].includes(event.key)) event.preventDefault();
    keys.add(event.key);
    const action = Object.keys(ACTIONS).find(id => ACTIONS[id].key === event.key);
    if (action && !event.repeat) selectAction(action);
    if (event.key === 'Enter' && !event.repeat) commit();
  }
});
window.addEventListener('keyup', event => keys.delete(event.key));
window.addEventListener('blur', () => { keys.clear(); drag = null; });

$('entry-form').addEventListener('submit', event => { event.preventDefault(); create(); });
$('practice').addEventListener('click', () => create(true));
$('join').addEventListener('click', () => {
  const identity = profile();
  if (!identity) return;
  const code = $('room-code').value.trim().toUpperCase();
  if (!/^[A-Z2-9]{6}$/.test(code)) { toast('请输入 6 位房间码。'); $('room-code').focus(); return; }
  send({ type: 'join', ...identity, code });
});
$('room-code').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); $('join').click(); } });
$('start').addEventListener('click', () => send({ type: 'start' }));
$('rematch').addEventListener('click', () => send({ type: 'rematch' }));
$('commit').addEventListener('click', commit);
document.querySelectorAll('.leave').forEach(button => button.addEventListener('click', () => { unlock(); send({ type: 'leave' }); }));
document.querySelectorAll('.character-card').forEach(button => button.addEventListener('click', () => selectCharacter(button.dataset.character)));
$('preview-move').addEventListener('click', () => play(previewActor, 'special', 1.45));
$('sound').addEventListener('click', () => {
  soundEnabled = !soundEnabled;
  $('sound').textContent = `声音 ${soundEnabled ? '开' : '关'}`;
  $('sound').setAttribute('aria-label', soundEnabled ? '关闭声音' : '开启声音');
  $('sound').setAttribute('aria-pressed', String(soundEnabled));
  tone(440, .12);
});
$('help').addEventListener('click', () => $('help-dialog').showModal());
$('close-help').addEventListener('click', () => $('help-dialog').close());
let lanUrls = [];
fetch('/api/lan').then(r => r.json()).then(({ urls }) => {
  lanUrls = urls;
  const target = $('lan-urls');
  target.textContent = urls.length ? `主机地址：${urls.join(' 或 ')}` : `主机地址：${location.origin}（使用主机的局域网 IP）`;
}).catch(() => { $('lan-urls').textContent = `主机地址：${location.origin}`; });
$('copy').addEventListener('click', async () => {
  const host = ['localhost', '127.0.0.1'].includes(location.hostname) ? lanUrls[0] || location.origin : location.origin;
  const invite = `${host}/?room=${room.code}`;
  try {
    if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(invite);
    else {
      const input = document.createElement('textarea'); input.value = invite;
      input.style.position = 'fixed'; input.style.left = '-9999px'; document.body.append(input); input.select();
      const copied = document.execCommand('copy'); input.remove();
      if (!copied) throw new Error('Copy unavailable');
    }
    toast('邀请地址已复制，好友打开后点击“加入房间”。');
  } catch { toast(`邀请地址：${invite}`); }
});
$('nickname').value = localStorage.getItem('asb-name') || '头号玩家';
const invitedRoom = new URLSearchParams(location.search).get('room');
if (invitedRoom && /^[A-Z2-9]{6}$/i.test(invitedRoom)) $('room-code').value = invitedRoom.toUpperCase();

const loader = new GLTFLoader();
Promise.all(Object.keys(CHARACTERS).map(async id => {
  const gltf = await loader.loadAsync(`/assets/${id}.glb`);
  if (gltf.animations.length < 7) throw new Error('Missing animation clips');
  models.set(id, gltf);
})).then(() => {
  $('model-status').textContent = '3 STARS / 21 ANIMATIONS';
  updatePreview();
  if (room) receiveRoom(room);
}).catch(error => {
  console.error('Character loading failed', error);
  $('model-status').textContent = '角色加载失败，请刷新';
  toast('角色文件加载失败，请确认安装完整后刷新页面。');
});
connect();
setInterval(() => { if (connected) send({ type: 'ping', sent: Date.now() }); }, 5000);

let previousFrame = performance.now();
function render(frameTime) {
  requestAnimationFrame(render);
  const dt = Math.min((frameTime - previousFrame) / 1000, .05); previousFrame = frameTime;
  if (document.hidden) return;
  const time = frameTime / 1000;
  timeline();
  const animationDt = frameTime < freezeUntil ? 0 : dt;
  for (const instance of actors) instance.mixer.update(animationDt);
  if (previewActor) previewActor.group.rotation.y = previewAngle;
  for (let i = sparks.length - 1; i >= 0; i--) {
    const item = sparks[i]; item.life -= dt;
    if (item.life <= 0) { scene.remove(item.spark); item.spark.material.dispose(); sparks.splice(i, 1); continue; }
    item.spark.position.addScaledVector(item.velocity, dt);
    item.velocity.y -= dt * 6; item.spark.material.opacity = item.life * 2;
  }
  shake *= Math.exp(-dt * 12); flash *= Math.exp(-dt * 10);
  $('flash').style.opacity = flash;
  if (room && room.deadline) {
    const seconds = Math.max(0, (room.deadline - now()) / 1000);
    $('countdown').textContent = room.stage === 'plan' ? seconds.toFixed(1) : room.stage === 'execute' ? '↯' : '—';
  }
  renderer.setScissorTest(false);
  renderer.setViewport(0, 0, innerWidth, innerHeight);
  renderer.clear();
  if (presentation === 'battle') {
    podium.visible = podiumRing.visible = false;
    viewmodel.visible = true;
    if (keys.has('ArrowLeft')) yaw = Math.min(.9, yaw + dt);
    if (keys.has('ArrowRight')) yaw = Math.max(-.9, yaw - dt);
    if (keys.has('ArrowUp')) pitch = Math.min(.5, pitch + dt);
    if (keys.has('ArrowDown')) pitch = Math.max(-.5, pitch - dt);
    // shortcut: fixed positions suit this 1v1 duel; add server-owned movement for free-roaming maps.
    camera.position.set(Math.sin(time * 83) * shake, 1.72 + Math.cos(time * 97) * shake * .5, 3.4);
    camera.rotation.order = 'YXZ'; camera.rotation.set(pitch, yaw, Math.sin(time * 56) * shake * .2);
    camera.fov = 55 + shake * 15; camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    animateHands(animationDt, time);
    renderer.render(scene, camera);
  } else {
    viewmodel.visible = false;
    podium.visible = podiumRing.visible = true;
    if (previewActor) previewActor.group.visible = true;
    let box;
    if (presentation === 'home') {
      const roster = document.querySelector('.roster').getBoundingClientRect();
      const cards = document.querySelector('.character-cards').getBoundingClientRect();
      const caption = document.querySelector('.character-caption').getBoundingClientRect();
      box = { left: roster.left, top: cards.bottom + 5, width: roster.width, height: Math.max(50, caption.top - cards.bottom - 5) };
    } else box = { left: innerWidth * .50, top: 145, width: innerWidth * .48, height: Math.max(200, innerHeight - 230) };
    previewCamera.position.set(2.8, 1.8, 5.7);
    previewCamera.lookAt(0, 1.36, 0);
    previewCamera.aspect = box.width / box.height; previewCamera.updateProjectionMatrix();
    renderer.setViewport(box.left, innerHeight - box.top - box.height, box.width, box.height);
    renderer.setScissor(box.left, innerHeight - box.top - box.height, box.width, box.height);
    renderer.setScissorTest(true);
    renderer.render(scene, previewCamera);
    renderer.setScissorTest(false);
  }
}
window.addEventListener('resize', () => renderer.setSize(innerWidth, innerHeight));
requestAnimationFrame(render);
