import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Raycaster, Vector3 } from 'three';
import { CHARACTERS } from '../shared/catalog.js';

test('each original GLB contains a skinned mesh, a complete rig and seven playable clips', async () => {
  for (const id of Object.keys(CHARACTERS)) {
    const data = await readFile(new URL(`../public/assets/${id}.glb`, import.meta.url));
    assert.equal(data.toString('ascii', 0, 4), 'glTF');
    assert.equal(data.readUInt32LE(4), 2);
    assert.equal(data.readUInt32LE(8), data.length);
    const jsonSize = data.readUInt32LE(12);
    const gltf = JSON.parse(data.toString('utf8', 20, 20 + jsonSize));
    assert.ok(gltf.skins?.[0]?.joints.length >= 16, `${id} needs a 16-bone rig`);
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
    const triangles = body.primitives.reduce((total, primitive) => total + gltf.accessors[primitive.indices].count / 3, 0);
    assert.ok(triangles < 80000, `${id} exceeded its browser geometry budget: ${triangles}`);
    assert.ok(data.length < 5 * 1024 * 1024, `${id} should load efficiently over a LAN`);
    const names = gltf.animations.map(a => a.name);
    for (const name of ['idle', 'attack', 'heavy', 'guard', 'special', 'hurt', 'victory']) {
      assert.ok(names.includes(name), `${id} missing ${name}: ${names}`);
      const clip = gltf.animations.find(a => a.name === name);
      assert.ok(clip.channels.length > 0);
      assert.ok(clip.samplers.every(s => gltf.accessors[s.input].count >= 2));
      if (['attack', 'heavy', 'guard', 'special'].includes(name)) {
        const times = gltf.accessors[clip.samplers[0].input];
        assert.ok(Math.abs(times.max[0] - 1.45) < .00001, `${id} ${name} must fit the 1450 ms combat slot`);
        assert.ok(clip.samplers.some(sampler => {
          const input = gltf.accessors[sampler.input];
          const view = gltf.bufferViews[input.bufferView];
          const offset = 28 + jsonSize + (view.byteOffset || 0) + (input.byteOffset || 0);
          return Array.from({ length: input.count }, (_, i) => data.readFloatLE(offset + i * 4))
            .some(time => Math.abs(time - .620) < .00001);
        }), `${id} ${name} needs an exact 620 ms contact pose`);
      }
    }
    assert.equal(gltf.images?.length || 0, 0, 'Models must not depend on external textures');
  }
});

test('angry keeps eyes open and independent expressions do not inherit blink geometry', async () => {
  for (const id of Object.keys(CHARACTERS)) {
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
