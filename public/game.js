import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { clone } from 'three/addons/utils/SkeletonUtils.js';
import { makeViewWeapon, weaponKind } from './weapons.js';
import { CHARACTERS, ACTIONS, TIMING, ROSTER, GROUPS } from '/shared/catalog.js';
import { portraitFor } from '/shared/portraits.js';
import { attackEnvelope, dampedSpring, opponentApproach, opponentOffsetX, presentationTime, WEAPON_CONTACT } from '/shared/presentation.js';

const $ = id => document.getElementById(id);
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const canvas = $('arena');
let selected = 'ikun', choice = 'strike', room = null, you = null, connected = false;
let clockOffset = 0, socket, toastTimer, soundEnabled = false, audio;
let previewActor, opponent, opponentId, presentation = 'home', previewAngle = -.18, previewCloseup = false, previewExpression = 'auto';
let yaw = 0, pitch = 0, drag = null, viewCharacter = null, lastTimeline = null;
let flash = 0, freezeUntil = 0, freezeStartedAt = 0, weaponMotion = null, shownHp = new Map();
const recoil = Object.fromEntries(['x', 'y', 'z', 'roll'].map(axis => [axis, { position: 0, velocity: 0 }]));
const startedEvents = new Set(), hitEvents = new Set(), logLines = [], keys = new Set();
const models = new Map();
const loadingModels = new Map(), motionLibraries = new Map();
const loader = new GLTFLoader();
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
  if (!models.has(selected)) { toast('角色正在入场，请稍候。'); return null; }
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
renderer.toneMappingExposure = 1.05;
renderer.autoClear = false;
renderer.setClearColor(0x111720);
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x111720, .03);
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, .05, 90);
const previewCamera = new THREE.PerspectiveCamera(34, 1, .05, 50);
const hemi = new THREE.HemisphereLight(0xbfd2e1, 0x22232a, 1.65);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xffdec0, 2.65);
key.position.set(-3, 7, 5);
key.castShadow = true;
key.shadow.mapSize.set(1024, 1024);
key.shadow.camera.left = key.shadow.camera.bottom = -9;
key.shadow.camera.right = key.shadow.camera.top = 9;
key.shadow.normalBias = .035;
scene.add(key);
const rim = new THREE.DirectionalLight(0x88bbd7, 1.9);
rim.position.set(4, 4, -4);
scene.add(rim);
const fill = new THREE.PointLight(0xedc9a0, 8, 20, 2);
fill.position.set(-2, 2.8, 2);
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
const railMaterial = new THREE.MeshStandardMaterial({ color: 0x8998aa, metalness: .65, roughness: .45, emissive: 0x263745, emissiveIntensity: .3 });
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

const viewmodelScene = new THREE.Scene();
const viewCamera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, .035, 12);
const viewmodel = new THREE.Group();
viewmodelScene.add(viewmodel, new THREE.HemisphereLight(0xd4e2ec, 0x24262e, 1.8));
const handKey = new THREE.DirectionalLight(0xffdfbe, 2.1);
handKey.position.set(-3, 4, 3);
const handFill = new THREE.DirectionalLight(0xa1c2db, .8);
handFill.position.set(3, 1, -2);
viewmodelScene.add(handKey, handFill);
scene.add(camera);
const hands = [];
for (const side of [-1, 1]) {
  const group = new THREE.Group();
  const sleeve = mesh(new THREE.CapsuleGeometry(.073, .30, 8, 16), 0x24232c, 0, .87);
  sleeve.rotation.x = Math.PI / 2;
  sleeve.position.set(0, -.028, .28);
  const wrist = mesh(new THREE.CapsuleGeometry(.052, .10, 8, 16), 0xca9674, 0, .72);
  wrist.rotation.x = Math.PI / 2;
  wrist.position.z = .065;
  const cuff = mesh(new THREE.TorusGeometry(.057, .016, 8, 24), 0x48444d, .1, .75);
  cuff.position.z = .135;
  const palm = mesh(new THREE.SphereGeometry(1, 24, 18), 0xca9674, 0, .72);
  palm.scale.set(.076, .048, .086);
  group.add(sleeve, wrist, cuff, palm);
  group.userData.skin = [wrist, palm];
  for (let i = 0; i < 4; i++) {
    const x = (i - 1.5) * .034;
    const finger = mesh(new THREE.CapsuleGeometry(.018, .034, 6, 12), 0xc18a69, 0, .72);
    finger.rotation.x = Math.PI / 2;
    finger.position.set(x, -.008, -.054);
    const knuckle = mesh(new THREE.SphereGeometry(.022, 12, 10), 0xd09a78, 0, .73);
    knuckle.scale.y = .65;
    knuckle.position.set(x, .025, -.055);
    group.add(finger, knuckle);
    group.userData.skin.push(finger, knuckle);
  }
  const thumb = mesh(new THREE.CapsuleGeometry(.021, .047, 6, 12), 0xd09a78, 0, .73);
  thumb.rotation.set(.85, side * .4, side * -.75);
  thumb.position.set(side * -.061, -.013, .008);
  group.add(thumb);
  group.userData.skin.push(thumb);
  group.userData.sleeve = sleeve;
  group.userData.cuff = cuff;
  group.position.set(side * .40, -.39, -1.10);
  group.rotation.z = side * -.20;
  viewmodel.add(group);
  hands.push(group);
}
let weapon, offhandWeapon;
function setViewmodel(character) {
  if (viewCharacter === character) return;
  viewCharacter = character;
  for (const [item, hand] of [[weapon, hands[1]], [offhandWeapon, hands[0]]]) {
    if (!item) continue;
    hand.remove(item);
    item.traverse(obj => { if (obj.isMesh) { obj.geometry.dispose(); obj.material.dispose(); } });
  }
  const props = makeViewWeapon(CHARACTERS[character]);
  weapon = props.right; offhandWeapon = props.left;
  if (weapon) hands[1].add(weapon);
  if (offhandWeapon) hands[0].add(offhandWeapon);
  const palette = CHARACTERS[character].visual || CHARACTERS[character].appearance;
  const skinColor = new THREE.Color(palette.skinColor);
  if (CHARACTERS[character].visual) skinColor.convertLinearToSRGB();
  for (const hand of hands) {
    hand.userData.sleeve.material.color.set(palette.bodyColor);
    hand.userData.cuff.material.color.set(palette.trimColor);
    if (CHARACTERS[character].visual) {
      hand.userData.sleeve.material.color.convertLinearToSRGB();
      hand.userData.cuff.material.color.convertLinearToSRGB();
    }
    hand.userData.skin.forEach(part => part.material.color.copy(skinColor));
  }
}

function actor(character) {
  const gltf = models.get(character);
  if (!gltf) return null;
  const model = clone(gltf.scene);
  model.traverse(obj => { if (obj.isMesh) {
    const photo = obj.material.name?.startsWith('Photo face · ');
    obj.castShadow = obj.receiveShadow = !photo;
  } });
  const group = new THREE.Group();
  group.add(model);
  scene.add(group);
  const mixer = new THREE.AnimationMixer(model);
  const clips = new Map(gltf.animations.map(clip => [clip.name.toLowerCase(), clip]));
  const morphs = [], bones = new Map();
  model.traverse(obj => {
    if (obj.morphTargetDictionary) morphs.push(obj);
    if (obj.isBone) bones.set(obj.name.toLowerCase(), obj);
  });
  const instance = { group, mixer, clips, morphs, bones, active: null, character, motion: null, fading: null, fadeRemaining: 0, hitAt: -Infinity, hitStrength: 0, nextBlink: performance.now() + 2600 + Math.random() * 1800, blinkAt: -Infinity, glance: 0 };
  mixer.addEventListener('finished', ({ action }) => {
    if (action === instance.active && !instance.motion) play(instance, 'idle');
  });
  actors.add(instance);
  play(instance, 'idle');
  return instance;
}
function removeActor(instance) {
  if (!instance) return;
  scene.remove(instance.group);
  instance.mixer.stopAllAction();
  instance.mixer.uncacheRoot(instance.group.children[0]);
  instance.group.traverse(obj => { if (obj.isSkinnedMesh) obj.skeleton.dispose(); });
  actors.delete(instance);
}
function play(instance, name, duration) {
  if (!instance) return;
  const clip = instance.clips.get(name) || [...instance.clips.entries()].find(([key]) => key.endsWith(name))?.[1];
  if (!clip) return;
  const next = instance.mixer.clipAction(clip);
  if (instance.active === next && name === 'idle') return;
  if (instance.fading && instance.fading !== next) instance.fading.stop();
  next.reset().setEffectiveWeight(1).setEffectiveTimeScale(1);
  next.setLoop(['idle', 'victory'].includes(name) ? THREE.LoopRepeat : THREE.LoopOnce, Infinity);
  next.clampWhenFinished = !['idle', 'victory'].includes(name);
  if (duration) next.setDuration(duration);
  if (instance.active && instance.active !== next) {
    instance.fading = instance.active;
    instance.fadeRemaining = .10;
    next.crossFadeFrom(instance.active, .10, false);
  } else instance.fading = null;
  next.play();
  instance.active = next;
  instance.activeName = name;
}

function hitStop(event) {
  if (reducedMotion || event.damage <= 0) return 0;
  return event.blocked ? 38 : event.action === 'special' ? 88 : event.action === 'heavy' ? 78 : 58;
}
function motionTime(motion) {
  return presentationTime(now() - motion.started, hitStop(motion.event));
}
function updateActor(instance, dt, frameTime) {
  if (instance.pendingHurtAt && frameTime >= instance.pendingHurtAt) {
    instance.pendingHurtAt = null;
    if (!instance.guarding && !instance.motion) play(instance, 'hurt', .44);
  }
  instance.mixer.update(dt);
  if (instance.motion && instance.active) {
    const elapsed = motionTime(instance.motion);
    if (elapsed < TIMING.slot) {
      instance.active.time = instance.active.getClip().duration * elapsed / TIMING.slot;
      instance.active.paused = false;
      instance.mixer.update(0);
    } else {
      instance.motion = null;
      if (!instance.guarding) play(instance, 'idle');
    }
  }
  if (instance.guarding && room?.stage === 'execute' && instance.activeName === 'guard') {
    const elapsed = Math.max(0, now() - room.timeline.started - TIMING.lead);
    instance.active.time = instance.active.getClip().duration * Math.min(TIMING.impact, elapsed * 3.4) / TIMING.slot;
    instance.active.paused = false;
    instance.mixer.update(0);
  }
  if (instance.fading) {
    instance.fadeRemaining -= dt;
    if (instance.fadeRemaining <= 0) { instance.fading.stop(); instance.fading = null; }
  }
  updateExpression(instance, dt, frameTime);
}
function updateExpression(instance, dt, frameTime) {
  const fighter = instance === opponent ? room?.players.find(p => p.id !== you) : null;
  const lowHp = fighter ? 1 - Math.min(1, (shownHp.get(fighter.id) ?? fighter.hp) / (CHARACTERS[fighter.character].hp * .4)) : 0;
  const sinceHit = Math.max(0, frameTime - instance.hitAt);
  const anger = Math.exp(-sinceHit / 1800) * instance.hitStrength;
  const pain = Math.exp(-sinceHit / 380) * instance.hitStrength;
  if (frameTime >= instance.nextBlink) {
    instance.blinkAt = frameTime;
    instance.nextBlink = frameTime + 3100 + Math.random() * 2700;
  }
  const blinkPhase = (frameTime - instance.blinkAt) / 150;
  const blink = blinkPhase >= 0 && blinkPhase <= 1 ? Math.sin(blinkPhase * Math.PI) ** 2 : 0;
  const override = instance === previewActor ? previewExpression : 'auto';
  const attacking = ['attack', 'heavy', 'special'].includes(instance.activeName);
  const expressions = {
    blink: override === 'auto' ? blink : 0,
    angry: override === 'angry' ? .9 : override === 'auto' ? Math.min(.85, anger * .65 + lowHp * .35 + (attacking ? .22 : instance.guarding ? .12 : 0)) : 0,
    hurt: override === 'hurt' ? .82 : override === 'auto' ? Math.max(pain * .8, instance.activeName === 'hurt' ? .6 : 0) : 0,
    smile: override === 'smile' ? .75 : override === 'auto' && instance.activeName === 'victory' ? .72 : 0,
  };
  for (const obj of instance.morphs) {
    for (const [name, value] of Object.entries(expressions)) {
      const index = obj.morphTargetDictionary[name];
      if (index !== undefined) obj.morphTargetInfluences[index] = value;
    }
  }
  if (reducedMotion || !instance.active) return;
  const head = instance.bones.get('head'), spine = instance.bones.get('spine');
  const idle = instance.activeName === 'idle';
  if (instance === opponent && head && idle) {
    const planning = room?.stage === 'plan';
    const glanceTarget = planning && Math.floor(frameTime / 2400) % 3 === 0 ? -.055 : 0;
    instance.glance += (glanceTarget - instance.glance) * (1 - Math.exp(-dt * 4));
    const targetYaw = THREE.MathUtils.clamp(Math.atan2(camera.position.x - instance.group.position.x, camera.position.z - instance.group.position.z) * .5, -.12, .12);
    head.rotation.y += targetYaw + instance.glance;
    head.rotation.x -= lowHp * .035;
  }
  if (spine) {
    if (sinceHit >= (instance.hitHold ?? 0)) spine.rotation.x -= Math.exp(-(sinceHit - (instance.hitHold ?? 0)) / 150) * instance.hitStrength * .06;
    if (idle && lowHp > 0) spine.rotation.x += lowHp * (.025 + Math.sin(frameTime / 410) * .009);
  }
}
function updatePreview() {
  if (!models.has(selected)) return;
  removeActor(previewActor);
  previewActor = actor(selected);
  previewActor.group.position.set(0, .12, 0);
  previewActor.group.rotation.y = previewAngle;
  podiumRing.material.color.set(CHARACTERS[selected].color);
  podiumRing.material.emissive.set(CHARACTERS[selected].color);
  pruneModels();
}
function framePortrait(image, portrait) {
  image.alt = portrait.alt;
  image.decoding = 'async';
  if (portrait.width > 0 && portrait.height > 0) {
    image.width = portrait.width; image.height = portrait.height;
  } else {
    image.removeAttribute('width'); image.removeAttribute('height');
  }
  image.style.setProperty('--portrait-position', portrait.objectPosition || '50% 50%');
  image.style.setProperty('--portrait-scale', String(Math.max(1, Number(portrait.scale) || 1)));
  Object.assign(image.style, { position: '', left: '', top: '', width: '', height: '', objectFit: '', transform: '' });
  if (portrait.crop) {
    const [x, y, w, h] = portrait.crop;
    Object.assign(image.style, { position: 'absolute', left: `${-x / w * 100}%`, top: `${-y / h * 100}%`,
      width: `${portrait.width / w * 100}%`, height: `${portrait.height / h * 100}%`, objectFit: 'fill', transform: 'none' });
  }
}
let portraitReferenceRequest = 0;
function updatePortraitReference(id) {
  const panel = $('photo-reference'), image = $('photo-reference-image'), source = $('photo-reference-source');
  const request = ++portraitReferenceRequest, portrait = portraitFor(id);
  $('preview-type').textContent = portrait ? '照片脸 / 表情与骨骼动作' : '风格化角色 / 表情与骨骼动作';
  panel.hidden = true;
  image.onload = image.onerror = null;
  image.removeAttribute('src');
  if (!portrait) return;
  const expectedSrc = new URL(portrait.src, location.href).href;
  framePortrait(image, portrait);
  source.href = portrait.sourceUrl;
  source.title = portrait.sourceTitle || '查看照片来源';
  source.textContent = '照片来源 ↗';
  image.onload = () => {
    if (request === portraitReferenceRequest && selected === id && image.currentSrc === expectedSrc) panel.hidden = false;
  };
  image.onerror = () => { if (request === portraitReferenceRequest) panel.hidden = true; };
  image.src = portrait.src;
}
function characterButton(id, archive = false) {
  const star = CHARACTERS[id];
  const button = document.createElement('button');
  button.className = 'character-card'; button.dataset.character = id;
  button.setAttribute('aria-label', `${star.name} ${star.subtitle}`);
  const num = document.createElement('span'); num.className = 'card-num'; num.textContent = GROUPS[star.group];
  const name = document.createElement('strong'); name.textContent = star.name;
  const subtitle = document.createElement('span'); subtitle.textContent = star.subtitle;
  const dot = document.createElement('i'); dot.className = 'card-dot';
  button.append(num, name, subtitle, dot);
  const portrait = portraitFor(id);
  if (portrait) {
    const frame = document.createElement('span'); frame.className = 'card-portrait'; frame.hidden = true;
    const image = document.createElement('img'); image.className = 'portrait-image';
    framePortrait(image, portrait);
    image.onload = () => { frame.hidden = false; button.classList.add('has-portrait'); };
    image.onerror = () => { frame.remove(); button.classList.remove('has-portrait'); };
    frame.append(image); button.append(frame); image.src = portrait.src;
  }
  if (archive) {
    const origin = document.createElement('span'); origin.className = 'card-origin'; origin.textContent = star.weapon;
    button.append(origin);
  }
  button.addEventListener('click', () => {
    $('roster-dialog').close();
    selectCharacter(id);
  });
  return button;
}
let rosterGroup = 'all';
function renderRoster() {
  const query = $('roster-search').value.trim().toLocaleLowerCase();
  const rows = ROSTER.filter(star => (rosterGroup === 'all' || star.group === rosterGroup) &&
    [star.name, star.subtitle, star.sourceWork, ...star.aliases].join(' ').toLocaleLowerCase().includes(query));
  const grid = $('roster-grid'); grid.replaceChildren();
  rows.forEach(star => grid.append(characterButton(star.id, true)));
  $('roster-results').textContent = rows.length ? `${rows.length} 位明星 · 点击入场` : '没有找到这位明星，换个名字试试。';
  document.querySelectorAll('.character-card').forEach(button => {
    button.classList.toggle('selected', button.dataset.character === selected);
    button.setAttribute('aria-pressed', String(button.dataset.character === selected));
  });
}
async function loadCharacter(id) {
  if (models.has(id)) {
    const gltf = models.get(id); models.delete(id); models.set(id, gltf); return gltf;
  }
  if (loadingModels.has(id)) return loadingModels.get(id);
  const request = (async () => {
    const star = CHARACTERS[id];
    const gltf = await loader.loadAsync(star.asset);
    gltf.scene.traverse(obj => {
      if (obj.isMesh && obj.material.name?.startsWith('Photo face · ')) {
        const previous = obj.material;
        obj.material = new THREE.MeshBasicMaterial({ name: previous.name, map: previous.map, vertexColors: previous.vertexColors,
          transparent: true, depthWrite: false, toneMapped: false });
        previous.dispose();
      }
    });
    if (!gltf.animations.length) {
      if (!motionLibraries.has(star.motion)) {
        const asset = ['ikun', 'wang', 'lubu'].includes(star.motion) ? `/assets/${star.motion}.glb` : `/assets/motions/${star.motion}.glb`;
        motionLibraries.set(star.motion, loader.loadAsync(asset).then(library => library.animations).catch(error => { motionLibraries.delete(star.motion); throw error; }));
      }
      gltf.animations = await motionLibraries.get(star.motion);
    }
    if (gltf.animations.length < 7) throw new Error(`${id}: missing motion clips`);
    models.set(id, gltf); pruneModels(); return gltf;
  })();
  loadingModels.set(id, request);
  try { return await request; } finally { loadingModels.delete(id); }
}
function pruneModels() {
  const retained = new Set([selected, ...[...actors].map(instance => instance.character), ...(room?.players.map(p => p.character) || [])]);
  for (const [id, gltf] of models) {
    if (models.size <= 12) break;
    if (retained.has(id)) continue;
    const geometries = new Set(), materials = new Set();
    gltf.scene.traverse(obj => {
      if (obj.geometry) geometries.add(obj.geometry);
      if (obj.material) (Array.isArray(obj.material) ? obj.material : [obj.material]).forEach(mat => materials.add(mat));
    });
    const textures = new Set();
    materials.forEach(mat => { Object.values(mat).forEach(value => { if (value?.isTexture) textures.add(value); }); mat.dispose(); });
    textures.forEach(texture => { texture.source?.data?.close?.(); texture.dispose(); });
    geometries.forEach(geometry => geometry.dispose());
    models.delete(id);
  }
}
async function selectCharacter(character) {
  if (!Object.hasOwn(CHARACTERS, character)) return;
  const same = selected === character && previewActor?.character === character;
  selected = character;
  document.documentElement.style.setProperty('--accent', CHARACTERS[character].color);
  document.querySelectorAll('.character-card').forEach(button => {
    button.classList.toggle('selected', button.dataset.character === character);
    button.setAttribute('aria-pressed', String(button.dataset.character === character));
  });
  $('special-name').textContent = CHARACTERS[character].special;
  $('character-description').textContent = CHARACTERS[character].description;
  $('selected-title').textContent = `${CHARACTERS[character].name} · ${CHARACTERS[character].weapon}`;
  $('character-origin').textContent = `出处：${CHARACTERS[character].sourceWork} ↗`;
  $('character-origin').href = CHARACTERS[character].sourceUrls[0];
  updatePortraitReference(character);
  if (same) return;
  if (previewActor) { removeActor(previewActor); previewActor = null; }
  $('model-status').textContent = `${ROSTER.length} 位明星 · ${CHARACTERS[character].name}入场中…`;
  $('create').disabled = $('practice').disabled = $('join').disabled = true;
  try {
    await loadCharacter(character);
    if (selected !== character) return;
    updatePreview();
    $('model-status').textContent = `${ROSTER.length} 位明星 · 已选${CHARACTERS[character].name}`;
    $('create').disabled = $('practice').disabled = $('join').disabled = false;
  } catch (error) {
    console.error('Character loading failed', error);
    if (selected === character) { $('model-status').textContent = '入场失败，点击角色重试'; toast('角色暂未入场，请点击重试。'); }
  }
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
    weaponMotion = null; freezeUntil = flash = 0;
    for (const axis of Object.values(recoil)) { axis.position = axis.velocity = 0; }
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
    const missing = room.players.filter(p => !models.has(p.character));
    if (missing.length) Promise.all(missing.map(p => loadCharacter(p.character))).then(() => {
      if (room?.stage === 'lobby') receiveRoom(room);
    }).catch(error => { console.error(error); toast('角色入场失败，请重新进入房间。'); });
    const ready = room.players.length === 2 && !missing.length;
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
  let createdOpponent = false;
  if (!opponent || opponentId !== other.id || opponent.character !== other.character) {
    if (!models.has(other.character)) {
      loadCharacter(other.character).then(() => {
        if (room?.players.some(p => p.id === other.id)) receiveRoom(room);
      }).catch(error => { console.error(error); toast('对手入场失败，请重新进入房间。'); });
    }
    removeActor(opponent);
    opponent = actor(other.character);
    createdOpponent = !!opponent;
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
  const sameExecution = previous?.stage === 'execute' && room.stage === 'execute' && previous.timeline.started === room.timeline.started;
  for (const p of room.players) if (!sameExecution || !shownHp.has(p.id)) shownHp.set(p.id, p.hp);
  if (room.stage === 'plan') {
    if (!previous || previous.stage !== 'plan' || previous.turn !== room.turn || previous.round !== room.round) {
      choice = ACTIONS[choice].cost <= self.energy ? choice : 'strike';
      weaponMotion = null; lastTimeline = null;
      if (opponent) { opponent.motion = null; opponent.guarding = false; opponent.group.position.set(0, 0, -1.8); play(opponent, 'idle'); }
    }
    $('phase').textContent = self.locked ? '等待对手' : '选择招式';
    $('turn-hint').textContent = !opponent ? '对手正在入场，加载完成即可选招。' : self.locked ? '招式已锁定，等待双方亮招。' : '读懂对手，锁定你的回合。';
  } else if (room.stage === 'execute') {
    $('phase').textContent = '出招！';
    $('turn-hint').textContent = '前摇 · 命中 · 收招';
    const identity = `${room.code}:${room.round}:${room.turn}:${room.timeline.started}`;
    if (lastTimeline !== identity) { startedEvents.clear(); hitEvents.clear(); lastTimeline = identity; }
    if (createdOpponent) {
      const event = room.timeline.events.find(item => item.actor === other.id);
      const elapsed = now() - room.timeline.started;
      if (event?.action === 'guard') { opponent.guarding = true; play(opponent, 'guard', TIMING.slot / 1000); }
      else if (event && elapsed >= event.start && elapsed < event.start + TIMING.slot) {
        opponent.motion = { started: room.timeline.started + event.start, event, action: event.action };
        play(opponent, event.action === 'strike' ? 'attack' : event.action, TIMING.slot / 1000);
      }
    }
  } else {
    weaponMotion = null;
    if (opponent) { opponent.motion = null; opponent.guarding = false; }
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
    button.disabled = room?.stage !== 'plan' || self?.locked || !opponent || action.cost > (self?.energy ?? 0);
    const key = document.createElement('span'); key.className = 'key'; key.textContent = action.key;
    const cost = document.createElement('span'); cost.className = 'cost'; cost.textContent = action.cost ? `${action.cost} ◆` : '+1 ◆';
    const title = document.createElement('strong'); title.textContent = action.name;
    const label = document.createElement('span'); label.className = 'action-label'; label.textContent = id === 'special' && self ? CHARACTERS[self.character].special : action.label;
    button.append(key, cost, title, label);
    button.addEventListener('click', () => selectAction(id)); target.append(button);
  }
  $('commit').disabled = room?.stage !== 'plan' || !self || self.locked || !opponent;
  $('commit').textContent = self?.locked ? '已经锁定 ✓' : '锁定招式 →';
}
function selectAction(action) {
  const self = room?.players.find(p => p.id === you);
  if (!self || !opponent || self.locked || room.stage !== 'plan' || ACTIONS[action].cost > self.energy) return;
  choice = action; renderActions(); tone(320, .06, 'sine', .03);
}
function commit() {
  const self = room?.players.find(p => p.id === you);
  if (room?.stage === 'plan' && !self.locked && opponent) send({ type: 'choose', action: choice });
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
  osc.connect(gain).connect(audio.destination); trackSound(osc, [gain]); osc.start(); osc.stop(audio.currentTime + duration);
}
const soundSources = new Set();
let noiseBuffer;
function trackSound(source, nodes = []) {
  soundSources.add(source);
  source.onended = () => { soundSources.delete(source); source.disconnect(); nodes.forEach(node => node.disconnect()); };
}
function noise(duration, volume, frequency, delay = 0, highpass = false) {
  if (!soundEnabled) return;
  audio ||= new (window.AudioContext || window.webkitAudioContext)();
  if (audio.state === 'suspended') audio.resume();
  if (!noiseBuffer) {
    noiseBuffer = audio.createBuffer(1, Math.ceil(audio.sampleRate * .35), audio.sampleRate);
    const samples = noiseBuffer.getChannelData(0);
    for (let i = 0; i < samples.length; i++) samples[i] = Math.random() * 2 - 1;
  }
  const source = audio.createBufferSource(), filter = audio.createBiquadFilter(), gain = audio.createGain();
  const start = audio.currentTime + delay;
  source.buffer = noiseBuffer;
  filter.type = highpass ? 'highpass' : 'lowpass';
  filter.frequency.setValueAtTime(frequency, start);
  filter.frequency.exponentialRampToValueAtTime(Math.max(120, frequency * .35), start + duration);
  gain.gain.setValueAtTime(.001, start);
  gain.gain.linearRampToValueAtTime(volume, start + .004);
  gain.gain.exponentialRampToValueAtTime(.001, start + duration);
  source.connect(filter).connect(gain).connect(audio.destination);
  trackSound(source, [filter, gain]); source.start(start); source.stop(start + duration);
}
function hitSound(event) {
  if (event.blocked) {
    noise(.08, .14, 3700, 0, true);
    tone(740, .12, 'triangle', .042, 380);
    tone(1120, .085, 'sine', .028, 800);
  } else {
    noise(.055, event.action === 'strike' ? .13 : .19, 2100);
    tone(event.action === 'special' ? 92 : 125, .19, 'sine', .15, 36);
    if (event.action !== 'strike') noise(.14, .055, 850);
  }
}
function impact(event) {
  if (event.damage <= 0) return;
  const localHit = event.target === you;
  shownHp.set(event.target, Math.max(0, (shownHp.get(event.target) ?? 0) - event.damage));
  updateHealth();
  if (!reducedMotion) {
    const power = event.blocked ? .45 : event.action === 'special' ? 1.3 : event.action === 'heavy' ? 1.1 : .8;
    recoil.x.position += (localHit ? -.018 : .010) * power;
    recoil.y.position += (localHit ? -.035 : .008) * power;
    recoil.z.position += (localHit ? .09 : .018) * power;
    recoil.roll.position += (localHit ? -.018 : .008) * power;
    recoil.z.velocity += (localHit ? .3 : .05) * power;
    const lateness = Math.max(0, now() - room.timeline.started - event.hit);
    freezeStartedAt = performance.now();
    freezeUntil = freezeStartedAt + Math.max(0, hitStop(event) - lateness);
    flash = localHit ? .19 : .035;
  }
  if (!localHit && opponent) {
    opponent.hitAt = performance.now();
    opponent.hitHold = hitStop(event);
    opponent.hitStrength = event.blocked ? .35 : event.action === 'special' ? 1 : .75;
    if (!event.blocked) opponent.pendingHurtAt = freezeUntil || performance.now();
  }
  const label = $('impact-label');
  label.textContent = `${event.blocked ? '格挡 · ' : event.action === 'special' ? '明星时刻 · ' : ''}−${event.damage}`;
  label.className = `impact-label show${localHit ? ' hurt' : ''}`;
  setTimeout(() => label.classList.remove('show'), 650);
  const actorName = room.players.find(p => p.id === event.actor).name;
  logLines.unshift(`${actorName} · ${event.title}${event.blocked ? '（格挡）' : ''} −${event.damage}`);
  logLines.length = Math.min(logLines.length, 4);
  const log = $('battle-log'); log.replaceChildren();
  logLines.forEach(line => { const div = document.createElement('div'); div.textContent = line; log.append(div); });
  hitSound(event);
  const contact = localHit && opponent ? WEAPON_CONTACT[opponent.character]?.[event.action] : null;
  const position = contact
    ? new THREE.Vector3(...contact).add(opponent.group.position)
    : new THREE.Vector3(.06, event.blocked ? 1.62 : 1.48, (opponent?.group.position.z ?? -1.8) + .30);
  spawnImpact(position, event);
}
const streakGeometry = new THREE.BoxGeometry(.007, .007, 1);
const impactRingGeometry = new THREE.TorusGeometry(.115, .005, 6, 48);
const effects = [];
function spawnImpact(position, event) {
  if (reducedMotion) return;
  const attacker = room.players.find(p => p.id === event.actor)?.character;
  const kind = weaponKind(CHARACTERS[attacker]);
  const color = event.blocked ? 0x91cdda : CHARACTERS[attacker]?.color || 0xffcf87;
  const size = Math.min(1, camera.position.distanceTo(position) / 1.7);
  const material = () => new THREE.MeshBasicMaterial({ color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
  const ring = new THREE.Mesh(impactRingGeometry, material());
  ring.position.copy(position); ring.quaternion.copy(camera.quaternion); ring.scale.setScalar(size);
  scene.add(ring); effects.push({ object: ring, age: 0, duration: event.blocked ? .22 : .16, kind: 'ring', size });
  const count = event.blocked ? 8 : 11;
  for (let i = 0; i < count; i++) {
    const angle = i * Math.PI * 2 / count + (event.blocked ? .15 : .4);
    const direction = new THREE.Vector3(Math.cos(angle), Math.sin(angle), .25 * Math.sin(i * 2.1));
    const streak = new THREE.Mesh(streakGeometry, material());
    streak.position.copy(position);
    streak.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), direction.clone().normalize());
    streak.scale.set(size, size, (.045 + i % 3 * .025) * size);
    scene.add(streak);
    effects.push({ object: streak, velocity: direction.multiplyScalar((event.blocked ? 1.5 : 2) * size), age: 0, duration: .14 + i % 3 * .025, kind: 'streak' });
  }
  if (['polearm', 'spear', 'staff', 'rake', 'knife', 'cleaver', 'sword', 'fan'].includes(kind)) {
    const points = [];
    for (let i = 0; i <= 16; i++) {
      const angle = -.7 + i / 16 * 1.4;
      points.push(new THREE.Vector3(Math.sin(angle) * .55, (Math.cos(angle) - 1) * .55, 0));
    }
    const slash = new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), new THREE.LineBasicMaterial({ color, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    slash.position.copy(position); slash.quaternion.copy(camera.quaternion); slash.rotateZ(kind === 'fan' ? .1 : -.65); slash.scale.setScalar(size);
    scene.add(slash); effects.push({ object: slash, age: 0, duration: .14, kind: 'slash', disposableGeometry: true });
  }
}

function timeline() {
  if (room?.stage !== 'execute' || !room.timeline) return;
  const elapsed = now() - room.timeline.started;
  const defender = room.timeline.events.find(event => event.actor !== you && event.action === 'guard');
  if (opponent && defender && !opponent.guarding) {
    opponent.guarding = true; opponent.motion = null;
    play(opponent, 'guard', TIMING.slot / 1000);
  }
  room.timeline.events.forEach((event, index) => {
    if (elapsed >= event.start && !startedEvents.has(index)) {
      startedEvents.add(index);
      const motion = { started: room.timeline.started + event.start, event, action: event.action };
      if (event.actor === you) weaponMotion = motion;
      else if (opponent && event.action !== 'guard') {
        opponent.motion = motion;
        play(opponent, event.action === 'strike' ? 'attack' : event.action, TIMING.slot / 1000);
      }
      if (event.action !== 'guard') {
        const character = room.players.find(p => p.id === event.actor)?.character;
        const release = event.action === 'strike' ? 365 : 445;
        const kind = weaponKind(CHARACTERS[character]);
        noise(['polearm', 'sword', 'staff', 'rake'].includes(kind) ? .21 : .16, .03, ['fan', 'mic'].includes(kind) ? 1600 : 950, Math.max(0, release - (elapsed - event.start)) / 1000);
      }
    }
  });
  if (opponent) {
    const pose = opponent.motion ? attackEnvelope(motionTime(opponent.motion), opponent.motion.action) : { extension: 0, windup: 0 };
    const reach = opponentApproach(opponent.character, opponent.motion?.action, opponent.motion?.event.blocked);
    opponent.group.position.z = -1.8 + pose.extension * reach - pose.windup * .12;
    opponent.group.position.x = pose.extension * opponentOffsetX(opponent.character, opponent.motion?.action);
  }
  room.timeline.events.forEach((event, index) => {
    if (elapsed >= event.hit && !hitEvents.has(index)) { hitEvents.add(index); impact(event); }
  });
}
function animateHands(time) {
  let drive = 0, ready = 0, follow = 0, guard = 0;
  let action = 'strike';
  const kind = weaponKind(CHARACTERS[viewCharacter || selected]);
  const longWeapon = ['polearm', 'spear', 'staff', 'baton', 'racket', 'pan', 'rake'].includes(kind);
  if (weaponMotion) {
    const elapsed = motionTime(weaponMotion);
    action = weaponMotion.action;
    if (elapsed >= TIMING.slot) weaponMotion = null;
    else ({ extension: drive, windup: ready, follow, guard } = attackEnvelope(elapsed, action));
  }
  if (room?.stage === 'execute' && room.timeline.events.some(event => event.actor === you && event.action === 'guard')) {
    guard = Math.min(1, Math.max(0, now() - room.timeline.started - TIMING.lead) / 180);
  }
  hands.forEach((hand, index) => {
    const sign = index === 0 ? -1 : 1;
    const bob = reducedMotion || weaponMotion || guard ? 0 : Math.sin(time * 1.3 + index * .6) * .003;
    hand.position.set(sign * .40 - sign * guard * .18, -.39 + bob + guard * .26, -1.10 + guard * .22);
    hand.rotation.set(guard * .65, 0, sign * -.20 - sign * guard * .55);
    if (index === 0) {
      hand.position.y += drive * .025;
      hand.position.z -= drive * (longWeapon ? .8 : kind === 'dualgun' ? 1.2 : .12);
      if (longWeapon) hand.position.x += drive * .18;
      return;
    }
    hand.position.z += ready * .18 - drive * (reducedMotion ? 3.7 : 1.5);
    if (['ball', 'melon', 'bowl', 'soup', 'fist', 'keyboard', 'book', 'phone', 'bag', 'pistol', 'dualgun'].includes(kind)) {
      hand.position.x += ready * .06 - drive * .32;
      hand.position.y += ready * (action === 'special' ? .68 : -.045) + drive * .19 - follow * .12;
      hand.rotation.x += ready * .24 - drive * .18;
      hand.rotation.y += drive * -.15;
      hand.rotation.z += ready * -.15 + drive * .30;
      if (action === 'heavy') {
        hand.position.x += ready * .12 - follow * .10;
        hand.position.y += ready * .18;
        hand.rotation.y += ready * -.35 + drive * .25;
        hand.rotation.z += drive * .22;
      }
    } else if (['fan', 'mic'].includes(kind)) {
      hand.position.x += ready * .10 - drive * .48 - follow * .10;
      hand.position.y += ready * .12 + drive * .10;
      hand.rotation.y += ready * -.6 + drive * .7;
      hand.rotation.z += ready * -.7 + drive * 1.15 + follow * .15;
      if (action === 'special') hands[0].position.y += drive * .16;
    } else if (['knife', 'cleaver', 'sword', 'fishfork', 'wrench', 'needle'].includes(kind)) {
      hand.position.x += ready * .12 - drive * .35 - follow * .14;
      hand.position.y += ready * .30 - drive * .03 - follow * .08;
      hand.rotation.z += ready * -.65 + drive * .70 + follow * .25;
      hand.rotation.y += ready * -.30 + drive * .45;
    } else {
      hand.position.x += ready * .08 - drive * .40 - follow * .18;
      hand.position.y += ready * (action === 'heavy' ? .50 : .24) + drive * .06 - follow * .16;
      hand.rotation.x += ready * -.15 - drive * .35;
      hand.rotation.z += ready * -.9 + drive * .65 + follow * .35;
      hand.rotation.y += drive * .15;
    }
  });
  return { drive, ready, guard, follow, action };
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
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(event.target.tagName) || $('help-dialog').open || $('roster-dialog').open) return;
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
['ikun', 'huaqiang', 'guatan', 'wang', 'lubu', 'chuanshanjia'].forEach(id => $('quick-roster').append(characterButton(id)));
$('roster-count').textContent = `${ROSTER.length} 位`;
Object.entries({ all: '全部', ...GROUPS }).forEach(([id, name]) => {
  const button = document.createElement('button'); button.textContent = name;
  button.dataset.group = id; button.setAttribute('aria-pressed', String(id === rosterGroup));
  button.addEventListener('click', () => {
    rosterGroup = id;
    $('roster-groups').querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item.dataset.group === id)));
    renderRoster();
  });
  $('roster-groups').append(button);
});
$('browse-roster').addEventListener('click', () => { renderRoster(); $('roster-dialog').showModal(); $('roster-search').focus(); });
$('roster-search').addEventListener('input', renderRoster);
$('close-roster').addEventListener('click', () => $('roster-dialog').close());
function previewMove() {
  const action = $('preview-action')?.value || 'special';
  play(previewActor, action, ['idle', 'victory'].includes(action) ? undefined : TIMING.slot / 1000);
}
$('preview-move').addEventListener('click', previewMove);
$('preview-action')?.addEventListener('change', previewMove);
$('preview-expression')?.addEventListener('change', event => { previewExpression = event.target.value; });
$('preview-closeup')?.addEventListener('click', () => {
  previewCloseup = !previewCloseup;
  $('preview-closeup').textContent = previewCloseup ? '查看全身' : '查看表情';
  $('preview-closeup').setAttribute('aria-pressed', String(previewCloseup));
});
$('sound').addEventListener('click', () => {
  soundEnabled = !soundEnabled;
  if (!soundEnabled) {
    for (const source of soundSources) { try { source.stop(); } catch {} }
    soundSources.clear();
  }
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

selectCharacter(selected);
connect();
setInterval(() => { if (connected) send({ type: 'ping', sent: Date.now() }); }, 5000);

let previousFrame = performance.now();
let idleTime = 0;
function render(frameTime) {
  requestAnimationFrame(render);
  const dt = Math.min((frameTime - previousFrame) / 1000, .05); previousFrame = frameTime;
  if (document.hidden) return;
  timeline();
  const animationDt = frameTime < freezeUntil ? 0 : dt;
  idleTime += animationDt;
  const expressionTime = frameTime < freezeUntil ? freezeStartedAt : frameTime;
  for (const instance of actors) updateActor(instance, animationDt, expressionTime);
  if (previewActor) previewActor.group.rotation.y = previewAngle;
  for (let i = effects.length - 1; i >= 0; i--) {
    const item = effects[i]; item.age += animationDt;
    if (item.age >= item.duration) {
      scene.remove(item.object); item.object.material.dispose();
      if (item.disposableGeometry) item.object.geometry.dispose();
      effects.splice(i, 1); continue;
    }
    const progress = item.age / item.duration;
    if (item.velocity) item.object.position.addScaledVector(item.velocity, animationDt);
    if (item.kind === 'ring') item.object.scale.setScalar(item.size * (1 + progress * 1.4));
    item.object.material.opacity = (1 - progress) ** 2;
  }
  for (const axis of Object.keys(recoil)) recoil[axis] = dampedSpring(recoil[axis].position, recoil[axis].velocity, animationDt);
  flash *= Math.exp(-dt * 14);
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
    const handPose = animateHands(idleTime);
    // shortcut: this dash is presentation only; add server-owned movement for free-roaming maps.
    const dash = reducedMotion ? 0 : handPose.drive * 2.2 - handPose.ready * .045;
    camera.position.set(recoil.x.position, 1.72 + recoil.y.position, 3.4 - dash + recoil.z.position);
    const incoming = opponent?.motion ? attackEnvelope(motionTime(opponent.motion), opponent.motion.action).extension : 0;
    const focus = reducedMotion ? 0 : Math.max(handPose.drive, incoming);
    camera.rotation.order = 'YXZ'; camera.rotation.set(pitch * (1 - focus), yaw * (1 - focus), recoil.roll.position);
    camera.fov = 55 + (reducedMotion ? 0 : handPose.drive * 1.5); camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    renderer.render(scene, camera);
    viewCamera.aspect = camera.aspect; viewCamera.fov = camera.fov; viewCamera.updateProjectionMatrix();
    renderer.clearDepth();
    renderer.render(viewmodelScene, viewCamera);
  } else {
    viewmodel.visible = false;
    podium.visible = podiumRing.visible = true;
    if (previewActor) previewActor.group.visible = true;
    let box;
    if (presentation === 'home') {
      box = $('preview-window').getBoundingClientRect();
    } else box = { left: innerWidth * .50, top: 145, width: innerWidth * .48, height: Math.max(200, innerHeight - 230) };
    previewCamera.position.set(previewCloseup ? .35 : 2.2, previewCloseup ? 2.03 : 1.85, previewCloseup ? 2.15 : 4.8);
    previewCamera.lookAt(0, previewCloseup ? 1.98 : 1.36, 0);
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
