import * as THREE from 'three';

const kinds = new Set(['ball', 'fan', 'polearm', 'cleaver', 'melon', 'mic', 'keyboard', 'book', 'fist', 'phone', 'bowl', 'racket', 'staff', 'pan', 'bag', 'knife', 'sword', 'soup', 'baton', 'fishfork', 'spear', 'wrench', 'dualgun', 'needle', 'pistol', 'rake']);
const originalKinds = { ikun: 'ball', wang: 'fan', lubu: 'polearm' };

export function weaponKind(star = {}) {
  const visual = String(star.visual?.weaponType || '').toLowerCase();
  const canonical = String(star.weaponType || originalKinds[star.id] || '').toLowerCase();
  return kinds.has(visual) ? visual : kinds.has(canonical) ? canonical : 'fist';
}

// Each mesh owns its geometry and material; the caller may dispose by traversal.
function mesh(geometry, color, metalness = 0, roughness = .68) {
  return new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color, metalness, roughness }));
}
function add(group, geometry, color, position = [0, 0, 0], rotation = [0, 0, 0], metalness = 0, roughness = .68) {
  const object = mesh(geometry, color, metalness, roughness);
  object.position.set(...position); object.rotation.set(...rotation); group.add(object);
  return object;
}
function box(group, size, color, position, metalness = 0) {
  return add(group, new THREE.BoxGeometry(...size), color, position, undefined, metalness);
}
function sphere(group, radius, color, position, scale = [1, 1, 1], metalness = 0) {
  const object = add(group, new THREE.SphereGeometry(radius, 24, 16), color, position, undefined, metalness);
  object.scale.set(...scale); return object;
}
function rod(group, a, b, radius, color, metalness = 0) {
  const from = new THREE.Vector3(...a), to = new THREE.Vector3(...b), delta = to.clone().sub(from);
  const object = add(group, new THREE.CylinderGeometry(radius, radius, delta.length(), 12), color, undefined, undefined, metalness);
  object.position.copy(from.add(to).multiplyScalar(.5));
  object.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), delta.normalize());
  return object;
}
function tube(group, points, radius, color, metalness = 0) {
  return add(group, new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map(p => new THREE.Vector3(...p))), Math.max(12, points.length * 2), radius, 6, false), color, undefined, undefined, metalness);
}
function shape(group, points, color, depth = .012, metalness = .65) {
  const outline = new THREE.Shape();
  points.forEach(([x, y], index) => index ? outline.lineTo(x, y) : outline.moveTo(x, y));
  outline.closePath();
  const object = add(group, new THREE.ExtrudeGeometry(outline, { depth, steps: 1, bevelEnabled: true, bevelThickness: .003, bevelSize: .003, bevelSegments: 1 }), color, [0, 0, -depth / 2], undefined, metalness, .4);
  return object;
}
function ring(group, radius, thickness, color, position, rotation = [0, 0, 0], metalness = .5) {
  return add(group, new THREE.TorusGeometry(radius, thickness, 8, 40), color, position, rotation, metalness);
}
function ball(group) {
  add(group, new THREE.SphereGeometry(.112, 40, 28), 0xb6521d, [0, 0, 0], undefined, 0, .86);
  for (const rotation of [[0, 0, 0], [Math.PI / 2, 0, 0], [0, Math.PI / 2, 0]]) ring(group, .1125, .0023, 0x34241f, [0, 0, 0], rotation, 0).material.roughness = .9;
  group.position.set(.025, .083, -.047);
}
function fan(group) {
  add(group, new THREE.CylinderGeometry(.012, .014, .29, 12), 0x674a2d);
  ring(group, .016, .005, 0xb99757, [0, .1, 0], [Math.PI / 2, 0, 0], .65);
  for (let i = 0; i < 9; i++) {
    const angle = (i - 4) * -.13, x = (i - 4) * .032, y = .235 - Math.abs(i - 4) * .011;
    const feather = sphere(group, 1, i % 2 ? 0xdacdb6 : 0xeee3ce, [x, y, 0], [.027, .145, .008]);
    feather.rotation.z = angle;
    add(group, new THREE.CylinderGeometry(.0018, .0012, .23, 5), 0xa89777, [x, y, .009], [0, 0, angle]);
  }
  group.position.set(.012, .03, -.04);
}
function foldingFan(group) {
  const edgeCount = 11, span = 2.12, inner = .079, outer = .205;
  for (let i = 0; i < edgeCount - 1; i++) {
    const angleA = -span / 2 + i * span / (edgeCount - 1), angleB = -span / 2 + (i + 1) * span / (edgeCount - 1);
    const point = (r, angle, edge) => [Math.sin(angle) * r, Math.cos(angle) * r, edge % 2 ? .005 : -.002];
    const a = point(inner, angleA, i), b = point(outer, angleA, i), c = point(outer, angleB, i + 1), d = point(inner, angleB, i + 1);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute([...a, ...b, ...c, ...a, ...c, ...d], 3));
    geometry.computeVertexNormals();
    const panel = add(group, geometry, i % 2 ? 0xe0dcc4 : 0xeee9d3, undefined, undefined, 0, .92);
    panel.material.side = THREE.DoubleSide; panel.name = `fan-paper-${i + 1}`;
  }
  for (let i = 0; i < edgeCount; i++) {
    const angle = -span / 2 + i * span / (edgeCount - 1);
    const rib = rod(group, [0, -.037, .007], [Math.sin(angle) * (outer + .008), Math.cos(angle) * (outer + .008), .007], i === 0 || i === edgeCount - 1 ? .004 : .002, 0x91704b);
    rib.name = `fan-bamboo-${i + 1}`;
  }
  sphere(group, .009, 0x9e7950, [0, -.028, .012], [1, 1, .35], .4);
  tube(group, [[-.076, .123, .012], [-.03, .146, .013], [.025, .13, .013], [.072, .147, .012]], .0016, 0x5c6556);
  box(group, [.012, .018, .002], 0xa55c48, [.067, .112, .013]);
  group.position.set(.017, .03, -.05); group.rotation.z = -.07;
}
function originalHalberd(group) {
  add(group, new THREE.CylinderGeometry(.013, .018, 1.3, 16), 0x3b2b25, undefined, undefined, .25);
  for (const y of [.22, .35, .53]) add(group, new THREE.CylinderGeometry(.025, .025, .035, 16), 0xa07a3b, [0, y, 0], undefined, .7);
  const blade = new THREE.Shape();
  blade.moveTo(0, .86); blade.lineTo(.044, .65); blade.lineTo(.018, .54); blade.lineTo(-.018, .54); blade.lineTo(-.044, .65); blade.closePath();
  const crescent = new THREE.Shape();
  crescent.moveTo(-.01, .34); crescent.bezierCurveTo(-.22, .37, -.24, .67, -.045, .75); crescent.bezierCurveTo(-.12, .60, -.10, .47, -.01, .45); crescent.closePath();
  for (const outline of [blade, crescent]) add(group, new THREE.ExtrudeGeometry(outline, { depth: .018, bevelEnabled: true, bevelThickness: .006, bevelSize: .005, bevelSegments: 2, steps: 1 }), 0xafbac2, [0, 0, -.009], undefined, .88, .29);
  add(group, new THREE.CapsuleGeometry(.026, .10, 6, 12), 0x7e2430, [.045, .36, 0], [0, 0, .35]);
  group.rotation.z = -.22; group.position.set(.035, .065, -.035);
}
function grip(group, trim, length = .115) {
  add(group, new THREE.CylinderGeometry(.018, .021, length, 12), 0x3b3130, [0, length * .15, 0]);
  for (const y of [-.025, .002, .027]) ring(group, .0205, .002, trim, [0, y, 0], [Math.PI / 2, 0, 0]);
}
function blade(group, kind, trim) {
  grip(group, trim);
  if (kind === 'cleaver') {
    shape(group, [[-.017, .06], [.098, .06], [.104, .245], [-.012, .266]], 0xbac5cd, .015);
    rod(group, [.103, .062, .011], [.109, .244, .011], .002, 0xe8eff2, .85);
    ring(group, .008, .0025, 0x667481, [.073, .23, .012]);
  } else {
    const width = kind === 'sword' ? .035 : .027, tip = kind === 'sword' ? .355 : .275;
    shape(group, [[-width, .065], [width, .065], [width * .6, tip - .04], [0, tip], [-width * .6, tip - .04]], 0xb9c8d1);
    rod(group, [0, .075, .01], [0, tip - .02, .01], .002, 0xe0e9ed, .8);
    box(group, [kind === 'sword' ? .12 : .065, .013, .027], trim, [0, .055, 0], .6);
  }
  group.position.set(.018, .03, -.055); group.rotation.z = -.15;
}
function melon(group) {
  sphere(group, .115, 0x53933e, [0, 0, 0], [1, 1.06, 1]);
  for (let i = 0; i < 9; i++) {
    const angle = i * Math.PI * 2 / 9, points = [];
    for (let j = 0; j <= 14; j++) {
      const theta = .08 + j / 14 * (Math.PI - .16);
      points.push([Math.sin(theta) * Math.cos(angle) * .116, Math.cos(theta) * .123, Math.sin(theta) * Math.sin(angle) * .116]);
    }
    tube(group, points, .006, 0x285b2e);
  }
  rod(group, [0, .12, 0], [.008, .146, .004], .007, 0x79654a);
  group.position.set(.02, .075, -.055);
}
function microphone(group, trim) {
  add(group, new THREE.CylinderGeometry(.018, .024, .22, 16), 0x303640, [0, .03, 0], undefined, .35);
  ring(group, .024, .006, trim, [0, .13, 0], [Math.PI / 2, 0, 0]);
  sphere(group, .056, 0x778792, [0, .179, 0], [1, 1.08, 1], .62);
  for (let i = -3; i <= 3; i++) {
    const y = i * .014, radius = Math.sqrt(.0565 ** 2 - y ** 2);
    ring(group, radius, .0015, 0x34414b, [0, .179 + y * 1.08, 0], [Math.PI / 2, 0, 0]);
  }
  for (let i = 0; i < 8; i++) {
    const a = i * Math.PI / 4, points = [];
    for (let j = 0; j <= 12; j++) {
      const t = .16 + j / 12 * (Math.PI - .32);
      points.push([Math.sin(t) * Math.cos(a) * .057, .179 + Math.cos(t) * .0615, Math.sin(t) * Math.sin(a) * .057]);
    }
    tube(group, points, .0014, 0x3b4955, .35);
  }
  box(group, [.008, .018, .003], trim, [0, .045, .023]);
  group.position.set(.015, .025, -.04); group.rotation.z = -.18;
}
function keyboard(group, trim) {
  box(group, [.284, .137, .022], 0x2f3640, [0, .058, 0], .25);
  box(group, [.275, .127, .005], trim, [0, .059, .013]);
  for (let row = 0; row < 4; row++) for (let col = 0; col < 11; col++) box(group, [.019, .016, .009], row === 0 ? 0x9faab1 : 0xd3d9d7, [(col - 5) * .023, .107 - row * .023, .019]);
  box(group, [.102, .014, .009], 0xc6ccca, [0, .012, .019]);
  for (const x of [-.104, -.074, .075, .105]) box(group, [.018, .014, .009], 0x9faab1, [x, .012, .019]);
  group.position.set(-.045, .03, -.055); group.rotation.set(.24, -.12, .07);
}
function book(group, body, trim) {
  box(group, [.145, .182, .036], 0xe1d5b5, [0, .098, 0]);
  for (const z of [-.025, .025]) box(group, [.158, .194, .01], body, [0, .098, z]);
  box(group, [.013, .194, .054], trim, [-.078, .098, 0]);
  box(group, [.09, .006, .003], trim, [.008, .14, .032]);
  box(group, [.062, .006, .003], trim, [.008, .125, .032]);
  box(group, [.024, .035, .003], trim, [.008, .076, .032]);
  for (const z of [-.012, -.004, .004, .012]) rod(group, [.074, .014, z], [.074, .183, z], .001, 0xaa9b7e);
  group.position.set(.018, .02, -.045); group.rotation.set(.06, -.18, -.08);
}
function phone(group, body, trim) {
  box(group, [.076, .154, .023], body, [0, .069, 0], .3);
  box(group, [.065, .118, .003], 0x223b53, [0, .075, .014], .1);
  box(group, [.043, .009, .001], 0x9cbfc8, [0, .115, .016]);
  for (let i = 0; i < 3; i++) box(group, [.043 - i * .006, .003, .002], trim, [0, .093 - i * .018, .016]);
  sphere(group, .006, trim, [0, .004, .014], [1, 1, .28]);
  box(group, [.018, .003, .002], 0x9ba2a6, [0, .135, .014]);
  group.position.set(.008, .04, -.035); group.rotation.z = -.09;
}
function bowl(group, soup, trim) {
  const profile = [[.032, -.035], [.053, -.02], [.083, .005], [.106, .055], [.108, .07]].map(([x, y]) => new THREE.Vector2(x, y));
  const shell = add(group, new THREE.LatheGeometry(profile, 36), soup ? 0x8b969b : 0xd8d3c0, [.01, .02, 0], undefined, soup ? .55 : .08);
  shell.material.side = THREE.DoubleSide;
  ring(group, .108, .007, soup ? 0xbdc5c7 : trim, [.01, .09, 0], [Math.PI / 2, 0, 0]);
  add(group, new THREE.CylinderGeometry(.032, .032, .008, 24), 0x928673, [.01, -.018, 0]);
  add(group, new THREE.CylinderGeometry(.101, .096, .012, 36), soup ? 0xc59a4f : 0xe8dbc0, [.01, .079, 0]);
  if (soup) {
    for (const [x, z] of [[-.04, .01], [.038, .03], [.01, -.045], [-.036, -.03]]) sphere(group, .012, 0x678b4e, [x, .087, z], [1, .16, .55]);
    for (const x of [-.055, .061]) rod(group, [x, .087, -.012], [x + .016, .087, .004], .005, 0xe1c77d);
  }
  rod(group, [.035, .1, .012], [.11, .195, .022], .006, 0xb7c2c6, .65);
  sphere(group, .018, 0xb7c2c6, [.037, .098, .011], [.8, .2, 1.35], .65);
  group.rotation.x = .15; group.position.set(.015, .035, -.07);
}
function racket(group, trim) {
  grip(group, trim, .14);
  rod(group, [-.014, .067, 0], [-.057, .125, 0], .008, trim, .25);
  rod(group, [.014, .067, 0], [.057, .125, 0], .008, trim, .25);
  const hoop = ring(group, 1, .052, trim, [0, .229, 0], undefined, .3);
  hoop.scale.set(.087, .113, .14);
  for (let i = -4; i <= 4; i++) {
    const x = i * .017, extent = .106 * Math.sqrt(1 - (x / .084) ** 2);
    rod(group, [x, .229 - extent, .002], [x, .229 + extent, .002], .0009, 0xdddcc3);
    const y = i * .021, width = .08 * Math.sqrt(1 - (y / .11) ** 2);
    rod(group, [-width, .229 + y, .003], [width, .229 + y, .003], .0009, 0xdddcc3);
  }
  group.position.set(.015, .03, -.045); group.rotation.z = -.14;
}
function pan(group, trim) {
  grip(group, trim, .14);
  add(group, new THREE.CylinderGeometry(.103, .105, .026, 36), 0x39414b, [0, .194, 0], [Math.PI / 2, 0, 0], .5);
  ring(group, .101, .007, 0x82929d, [0, .194, .018]);
  add(group, new THREE.CircleGeometry(.094, 36), 0x242a30, [0, .194, .016], undefined, .3);
  for (const y of [.098, .12]) sphere(group, .005, trim, [0, y, .019], [1, 1, .45], .65);
  group.position.set(.014, .03, -.05); group.rotation.z = -.1;
}
function bag(group, body, trim, name) {
  shape(group, [[-.07, -.025], [.07, -.025], [.096, .166], [-.096, .166]], body, .077, 0);
  tube(group, [[-.052, .165, 0], [-.05, .221, 0], [0, .244, 0], [.05, .221, 0], [.052, .165, 0]], .009, trim);
  box(group, [.109, .093, .01], trim, [0, .063, .047]);
  for (const x of [-.068, .068]) box(group, [.012, .159, .005], 0x66584b, [x, .065, .043]);
  if (name.includes('肥料') || name.includes('养分')) {
    rod(group, [0, .034, .055], [0, .102, .055], .002, 0xe6d39a);
    for (const y of [.051, .071, .09]) for (const side of [-1, 1]) {
      const leaf = sphere(group, .009, 0xe6d39a, [side * .01, y, .056], [.55, 1.2, .3]); leaf.rotation.z = side * -.65;
    }
  } else ring(group, .015, .003, 0xddd3a9, [0, .067, .055], undefined, 0);
  group.position.set(.015, .035, -.065); group.rotation.z = -.08;
}
function fork(group, spear, trim) {
  grip(group, trim);
  rod(group, [0, .045, 0], [0, .24, 0], .008, 0x9bafb9, .7);
  if (spear) shape(group, [[-.027, .239], [0, .354], [.027, .239]], 0xbdcbd3);
  else {
    rod(group, [-.054, .237, 0], [.054, .237, 0], .008, 0xb7c7cc, .7);
    for (const x of [-.054, 0, .054]) {
      rod(group, [x, .238, 0], [x, .315, 0], .006, 0xb7c7cc, .7);
      add(group, new THREE.ConeGeometry(.007, .025, 10), 0xd1dce0, [x, .325, 0], undefined, .75);
    }
  }
  group.position.set(.015, .035, -.055); group.rotation.z = -.12;
}
function rake(group, trim) {
  grip(group, trim);
  rod(group, [0, .045, 0], [0, .231, 0], .012, 0x695546);
  add(group, new THREE.CylinderGeometry(.019, .016, .034, 12), 0xb5bfc3, [0, .217, 0], undefined, .65);
  rod(group, [-.117, .242, 0], [.117, .242, 0], .011, 0xaab7bd, .65);
  for (let i = 0; i < 9; i++) {
    const x = (i - 4) * .026;
    const tooth = tube(group, [[x, .244, 0], [x, .277, -.002], [x, .306, -.022]], .0055, 0xc0cbd0, .7);
    tooth.name = `rake-tooth-${i + 1}`;
    const tip = add(group, new THREE.ConeGeometry(.006, .019, 10), 0xd5dfe2, [x, .313, -.027], undefined, .75);
    tip.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(0, .016, -.014).normalize());
  }
  group.position.set(.013, .025, -.045); group.rotation.z = -.11;
}
function wrench(group, trim) {
  grip(group, trim);
  shape(group, [[-.015, .045], [.015, .045], [.023, .194], [.063, .22], [.067, .27], [.045, .29], [.034, .244], [-.028, .244], [-.042, .291], [-.066, .271], [-.061, .224], [-.022, .194]], 0xa8bbc4, .02);
  ring(group, .008, .003, 0x71858f, [0, .099, .014]);
  group.position.set(.015, .03, -.045); group.rotation.z = -.14;
}
function gun(group, body, trim) {
  box(group, [.047, .111, .045], 0x394046, [0, -.008, 0]);
  box(group, [.055, .049, .165], body, [0, .071, -.068], .45);
  box(group, [.049, .012, .14], 0x9aadb6, [0, .1, -.067], .7);
  add(group, new THREE.CylinderGeometry(.014, .014, .055, 16), 0x667d8b, [0, .072, -.165], [Math.PI / 2, 0, 0], .6);
  ring(group, .013, .003, trim, [0, .072, -.194]);
  box(group, [.028, .039, .022], trim, [0, .027, -.039]);
  box(group, [.008, .008, .015], trim, [0, .111, -.14]);
  group.position.set(.008, .02, -.04);
}
function staff(group, star, trim) {
  const name = star.weapon || '';
  if (star.id === 'wukong') {
    rod(group, [0, -.065, 0], [0, .285, 0], .015, 0x783e30, .35);
    for (const y of [-.047, .267]) {
      add(group, new THREE.CylinderGeometry(.022, .022, .055, 16), 0xd0a553, [0, y, 0], undefined, .72, .4);
      for (const offset of [-.019, .019]) ring(group, .022, .003, 0x92723b, [0, y + offset, 0], [Math.PI / 2, 0, 0]);
    }
    group.position.set(.014, .025, -.045); group.rotation.z = -.12;
    return;
  }
  grip(group, trim);
  rod(group, [0, .04, 0], [0, .295, 0], .01, 0x776345);
  if (star.id === 'tangseng' || name.includes('九环')) {
    ring(group, .044, .006, 0xd9ad4f, [0, .281, 0], undefined, .7);
    const positions = [-1, 1].flatMap(side => [.267, .243, .219].map(y => [side * .039, y, .008]));
    positions.push([0, .22, .01], [0, .194, .01], [0, .168, .01]);
    positions.forEach((position, index) => {
      const hangingRing = ring(group, .011, .0025, 0xd9ad4f, position, undefined, .7);
      hangingRing.name = `staff-hanging-ring-${index + 1}`;
    });
  } else if (name.includes('笛')) {
    for (let i = 0; i < 6; i++) sphere(group, .004, 0x302b28, [0, .07 + i * .033, .01], [1, 1, .25]);
  } else if (name.includes('面筋')) {
    for (let i = 0; i < 4; i++) {
      const bite = add(group, new THREE.CapsuleGeometry(.022, .029, 4, 12), i % 2 ? 0xad7034 : 0xcc9650, [0, .13 + i * .045, 0]); bite.rotation.z = (i % 2 ? 1 : -1) * .2;
    }
  } else if (name.includes('冰淇淋')) {
    add(group, new THREE.ConeGeometry(.04, .09, 20), 0xca9d60, [0, .248, 0], [0, 0, Math.PI]);
    for (const [radius, y] of [[.047, .295], [.039, .319], [.028, .34]]) sphere(group, radius, 0xede7d7, [0, y, 0], [1, .55, 1]);
  } else if (name.includes('鸡')) {
    sphere(group, .047, 0xe2d092, [0, .283, 0], [1, 1.2, .65]);
    shape(group, [[.04, .287], [.067, .275], [.04, .267]], 0xce8d39, .018, 0);
    sphere(group, .004, 0x272c32, [.017, .305, .033]);
    for (const x of [-.021, 0, .021]) sphere(group, .012, 0xb54b40, [x, .334, 0], [.85, 1.2, .65]);
  } else if (name.includes('笔')) {
    rod(group, [-.036, .03, 0], [-.036, .24, 0], .007, trim);
    sphere(group, .034, 0xb74a3f, [-.036, .273, 0], [1, 1, .7]);
    sphere(group, .039, 0xd1af50, [.012, .273, 0], [.8, 1.3, .7]);
    for (const x of [-.012, .012, .033]) rod(group, [.012, .315, 0], [x, .348, 0], .005, 0x5f8050);
  } else {
    ring(group, .043, .009, trim, [0, .275, 0]);
    sphere(group, .026, 0x98b6c2, [0, .275, 0], [.7, 1, .7], .5);
    ring(group, .013, .004, trim, [0, .18, 0], [Math.PI / 2, 0, 0]);
  }
  group.position.set(.015, .025, -.045); group.rotation.z = -.12;
}
function boxingGlove(group, body, trim, side) {
  sphere(group, .078, body, [0, .018, -.041], [1, .79, 1.15]);
  sphere(group, .032, body, [-side * .063, -.014, .006], [.66, 1, 1.08]);
  ring(group, .047, .009, trim, [0, .002, .05], undefined, 0);
  box(group, [.058, .025, .008], trim, [0, .018, .058]);
  rod(group, [-.04, .024, .034], [.04, .024, .034], .0018, 0x6c6259);
  group.userData.weaponKind = 'fist';
}

export function makeViewWeapon(star = {}) {
  const right = new THREE.Group(), kind = weaponKind(star);
  const body = star.visual?.bodyColor || star.appearance?.bodyColor || star.bodyColor || 0x556978;
  const trim = star.visual?.trimColor || star.appearance?.trimColor || star.trimColor || star.color || 0xc4af7c;
  right.userData.weaponKind = kind;
  switch (kind) {
    case 'ball': ball(right); break;
    case 'fan':
      if (star.visual?.fanStyle === 'folding') foldingFan(right);
      else fan(right);
      break;
    case 'polearm':
      if (star.id === 'lubu') originalHalberd(right);
      else if ((star.weapon || '').includes('旗')) {
        fork(right, true, trim);
        shape(right, [[.014, .15], [.157, .18], [.126, .29], [.014, .32]], body, .005, 0);
      } else fork(right, true, trim);
      break;
    case 'knife': case 'sword': case 'cleaver': blade(right, kind, trim); break;
    case 'melon': melon(right); break;
    case 'mic': microphone(right, trim); break;
    case 'keyboard': keyboard(right, trim); break;
    case 'book': book(right, body, trim); break;
    case 'phone': phone(right, body, trim); break;
    case 'bowl': case 'soup': bowl(right, kind === 'soup', trim); break;
    case 'racket': racket(right, trim); break;
    case 'pan': pan(right, trim); break;
    case 'bag': bag(right, body, trim, star.weapon || ''); break;
    case 'staff': staff(right, star, trim); break;
    case 'fishfork': case 'spear': fork(right, kind === 'spear', trim); break;
    case 'rake': rake(right, trim); break;
    case 'wrench': wrench(right, trim); break;
    case 'baton':
      grip(right, trim); rod(right, [0, .05, 0], [0, .32, 0], .016, body);
      rod(right, [0, .082, 0], [.09, .082, 0], .013, 0x39444d);
      right.position.set(.015, .025, -.045); right.rotation.z = -.15; break;
    case 'needle':
      rod(right, [0, -.025, 0], [0, .24, 0], .006, 0xbdcbd2, .7);
      ring(right, .012, .004, trim, [0, .257, 0]);
      add(right, new THREE.ConeGeometry(.006, .041, 10), 0xdae4e8, [0, -.045, 0], [0, 0, Math.PI], .7);
      right.position.set(.01, .015, -.035); break;
    case 'pistol': gun(right, body, trim); break;
    case 'dualgun': {
      gun(right, body, trim);
      const left = new THREE.Group(); gun(left, body, trim);
      left.position.x *= -1; left.userData.weaponKind = kind;
      return { right, left };
    }
    case 'fist':
      if (star.visual?.gloves) {
        boxingGlove(right, body, trim, 1);
        const left = new THREE.Group(); boxingGlove(left, body, trim, -1);
        return { right, left };
      } else if ((star.weapon || '').includes('拳套') || star.id === 'lanlanlu') {
        sphere(right, .07, star.id === 'lanlanlu' ? 0xeee8d6 : body, [0, .008, -.031], [1, .85, 1.08]);
        ring(right, .046, .009, trim, [0, 0, .033]);
      }
      break;
  }
  if (kind === 'sword' || kind === 'spear' || kind === 'racket') right.scale.setScalar(.96);
  return { right };
}
