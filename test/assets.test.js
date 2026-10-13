import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
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
    const names = gltf.animations.map(a => a.name);
    for (const name of ['idle', 'attack', 'heavy', 'guard', 'special', 'hurt', 'victory']) {
      assert.ok(names.includes(name), `${id} missing ${name}: ${names}`);
      const clip = gltf.animations.find(a => a.name === name);
      assert.ok(clip.channels.length > 0);
      assert.ok(clip.samplers.every(s => gltf.accessors[s.input].count >= 2));
    }
    assert.equal(gltf.images?.length || 0, 0, 'Models must not depend on external textures');
  }
});
