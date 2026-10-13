import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Raycaster, Vector3 } from 'three';
import { CHARACTERS } from '../shared/catalog.js';

const originals = new Set(['ikun', 'wang', 'lubu']);
const photoFaces = new Set(['ikun', 'huaqiang', 'guatan']);
const boneNames = ['root', 'hips', 'spine', 'head', ...['L', 'R'].flatMap(side => ['upper', 'forearm', 'hand', 'thigh', 'shin', 'foot'].map(bone => `${bone}.${side}`))];

async function readGLB(asset) {
  const data = await readFile(new URL(`../public${asset}`, import.meta.url));
  assert.equal(data.toString('ascii', 0, 4), 'glTF', asset);
  assert.equal(data.readUInt32LE(4), 2, asset);
  assert.equal(data.readUInt32LE(8), data.length, asset);
  const jsonSize = data.readUInt32LE(12);
  return { data, gltf: JSON.parse(data.toString('utf8', 20, 20 + jsonSize)), binaryOffset: 28 + jsonSize };
}
function values(glb, accessorIndex) {
  const accessor = glb.gltf.accessors[accessorIndex];
  assert.equal(accessor.componentType, 5126, 'Animation and morph samples should be floats');
  const components = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4 }[accessor.type];
  const view = glb.gltf.bufferViews[accessor.bufferView];
  const offset = glb.binaryOffset + (view?.byteOffset || 0) + (accessor.byteOffset || 0);
  const stride = view?.byteStride || components * 4;
  const result = Array.from({ length: accessor.count }, (_, vertex) => Array.from({ length: components }, (_, axis) => view ? glb.data.readFloatLE(offset + vertex * stride + axis * 4) : 0));
  if (accessor.sparse) {
    const sparse = accessor.sparse;
    const indices = glb.gltf.bufferViews[sparse.indices.bufferView];
    const samples = glb.gltf.bufferViews[sparse.values.bufferView];
    const indexOffset = glb.binaryOffset + (indices.byteOffset || 0) + (sparse.indices.byteOffset || 0);
    const sampleOffset = glb.binaryOffset + (samples.byteOffset || 0) + (sparse.values.byteOffset || 0);
    const [bytes, read] = ({ 5121: [1, 'readUInt8'], 5123: [2, 'readUInt16LE'], 5125: [4, 'readUInt32LE'] })[sparse.indices.componentType];
    for (let i = 0; i < sparse.count; i++) {
      const vertex = glb.data[read](indexOffset + i * bytes);
      for (let axis = 0; axis < components; axis++) result[vertex][axis] = glb.data.readFloatLE(sampleOffset + (i * components + axis) * 4);
    }
  }
  return result;
}
function checkClips(glb, id) {
  const { gltf } = glb;
  const names = gltf.animations?.map(animation => animation.name) || [];
  for (const name of ['idle', 'attack', 'heavy', 'guard', 'special', 'hurt', 'victory']) {
    assert.ok(names.includes(name), `${id} missing ${name}: ${names}`);
    const clip = gltf.animations.find(animation => animation.name === name);
    assert.ok(clip.channels.length > 0);
    assert.ok(clip.samplers.every(sampler => gltf.accessors[sampler.input].count >= 2));
    if (['attack', 'heavy', 'guard', 'special'].includes(name)) {
      const times = clip.samplers.map(sampler => values(glb, sampler.input).flat());
      assert.ok(Math.abs(Math.max(...times.flat()) - 1.45) < .00001, `${id} ${name} must fit the 1450 ms combat slot`);
      assert.ok(times.some(samples => samples.some(time => Math.abs(time - .620) < .00001)), `${id} ${name} needs an exact 620 ms contact pose`);
    }
  }
}

test('every character has a facial rig within the browser budget and all motion families have seven compatible clips', async () => {
  const motionFiles = new Map();
  for (const [id, character] of Object.entries(CHARACTERS)) {
    const model = await readGLB(character.asset);
    const { data, gltf } = model;
    const joints = gltf.skins?.[0]?.joints;
    assert.ok(joints?.length >= 16, `${id} needs a 16-bone rig`);
    const rigNames = joints.map(index => gltf.nodes[index].name);
    for (const bone of boneNames) assert.ok(rigNames.includes(bone), `${id} needs compatible bone ${bone}`);
    assert.ok(gltf.meshes?.length > 0);
    const expressions = ['blink', 'angry', 'smile', 'hurt'];
    const body = gltf.meshes.find(mesh => expressions.every(name => mesh.extras?.targetNames?.includes(name)));
    assert.ok(body, `${id} needs independently controllable facial expressions`);
    for (const name of expressions) {
      const index = body.extras.targetNames.indexOf(name);
      assert.ok(body.primitives.some(primitive => {
        const positions = gltf.accessors[primitive.targets[index].POSITION];
        return [...positions.min, ...positions.max].some(value => Math.abs(value) > .0001);
      }), `${id} facial control ${name} must move geometry`);
    }
    const morphIndices = expressions.map(name => body.extras.targetNames.indexOf(name));
    const morphs = body.primitives.map(primitive => morphIndices.map(index => values(model, primitive.targets[index].POSITION)));
    for (let a = 0; a < expressions.length; a++) {
      for (let b = a + 1; b < expressions.length; b++) {
        assert.ok(morphs.some(primitive => primitive[a].some((vector, vertex) => vector.some((value, axis) => Math.abs(value - primitive[b][vertex][axis]) > .0001))), `${id} ${expressions[a]} and ${expressions[b]} need distinct geometry`);
      }
    }
    const triangles = gltf.meshes.reduce((total, mesh) => total + mesh.primitives.reduce((sum, primitive) => sum + gltf.accessors[primitive.indices].count / 3, 0), 0);
    assert.ok(triangles < 80000, `${id} exceeded its browser geometry budget: ${triangles}`);
    assert.ok(data.length < 5 * 1024 * 1024, `${id} should load efficiently over a LAN`);
    assert.equal(gltf.images?.length || 0, photoFaces.has(id) ? 1 : 0, `${id} embedded photo count`);
    for (const image of gltf.images || []) {
      assert.equal(image.uri, undefined, `${id} must not request external photos`);
      assert.ok(Number.isInteger(image.bufferView), `${id} image must be embedded`);
      assert.ok(['image/png', 'image/jpeg'].includes(image.mimeType), `${id} image format`);
    }
    if (photoFaces.has(id)) {
      const material = gltf.materials.findIndex(mat => mat.name === `Photo face · ${id}`);
      assert.ok(material >= 0, `${id} photo material is bound`);
      const face = body.primitives.find(primitive => primitive.material === material);
      assert.ok(face && Number.isInteger(face.attributes.TEXCOORD_0), `${id} photo has UV mapping`);
      const uv = values(model, face.attributes.TEXCOORD_0).flat();
      assert.ok(uv.every(v => v >= 0 && v <= 1), `${id} UVs stay in the verified photograph`);
    }
    if (originals.has(id)) {
      checkClips(model, id);
      continue;
    }
    assert.equal(gltf.animations?.length || 0, 0, `${id} should share a motion family instead of duplicating animation data`);
    if (!motionFiles.has(character.motion)) {
      const motion = await readGLB(`/assets/motions/${character.motion}.glb`);
      checkClips(motion, character.motion);
      const animatedBones = new Set(motion.gltf.animations.flatMap(clip => clip.channels.map(channel => motion.gltf.nodes[channel.target.node].name)));
      for (const bone of boneNames) assert.ok(animatedBones.has(bone), `${character.motion} motion must animate ${bone}`);
      assert.equal(motion.gltf.meshes?.length || 0, 0, 'Reusable motions should only contain a rig');
      motionFiles.set(character.motion, motion);
    }
    const motionNodes = new Set(motionFiles.get(character.motion).gltf.nodes.map(node => node.name));
    for (const bone of rigNames) assert.ok(motionNodes.has(bone), `${id} rig must bind to ${character.motion} motion bone ${bone}`);
  }
  assert.deepEqual([...motionFiles.keys()].sort(), ['brawler', 'knife', 'orb', 'staff']);
});

test('angry keeps eyes open and independent expressions do not inherit blink geometry', async () => {
  for (const id of ['wang', 'lubu']) {
    const data = await readFile(new URL(`../public/assets/${id}.glb`, import.meta.url));
    const { scene } = await new GLTFLoader().parseAsync(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength), '');
    scene.updateMatrixWorld(true);
    scene.traverse(mesh => {
      if (!mesh.isSkinnedMesh) return;
      mesh.skeleton.update();
      const positions = mesh.geometry.attributes.position;
      const smile = mesh.geometry.morphAttributes.position[mesh.morphTargetDictionary.smile];
      const hurt = mesh.geometry.morphAttributes.position[mesh.morphTargetDictionary.hurt];
      for (let i = 0; i < positions.count; i++) {
        if (positions.getY(i) < 2) continue;
        assert.ok(Math.hypot(smile.getX(i), smile.getY(i), smile.getZ(i)) < .00001, `${id} smile must not inherit another expression around the eyes`);
        assert.ok(Math.abs(hurt.getZ(i)) < .00001, `${id} hurt must not inherit blink's eye retraction`);
      }
      mesh.morphTargetInfluences[mesh.morphTargetDictionary.angry] = .9;
    });
    const eye = new Raycaster(new Vector3(-.093, 2.024, 2), new Vector3(0, 0, -1)).intersectObject(scene, true)[0];
    const white = new Raycaster(new Vector3(-.069, 2.022, 2), new Vector3(0, 0, -1)).intersectObject(scene, true)[0];
    assert.equal(eye?.object.material.name, 'Ink · eyelids and pupils', `${id} angry must leave the iris visible`);
    assert.equal(white?.object.material.name, 'Ivory linen', `${id} angry must leave eye white visible`);
  }
});
