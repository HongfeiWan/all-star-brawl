import test from 'node:test';
import assert from 'node:assert/strict';
import { readdir, readFile } from 'node:fs/promises';
import { ROSTER, GROUPS, CHARACTERS } from '../shared/catalog.js';
import { ROSTER_MOTIONS, ROSTER_CONTACT, ROSTER_VISUAL } from '../shared/roster-contacts.js';
import { newFighter } from '../src/combat.js';

const originals = new Set(['ikun', 'wang', 'lubu']);
const families = new Set(['knife', 'orb', 'staff', 'brawler']);

test('the researched roster is the only character catalog and every entry is a valid fighter', () => {
  assert.ok(Object.isFrozen(CHARACTERS));
  assert.equal(ROSTER.length, Object.keys(CHARACTERS).length);
  assert.equal(new Set(ROSTER.map(row => row.id)).size, ROSTER.length);
  assert.ok(CHARACTERS.huaqiang && CHARACTERS.guatan, 'Huaqiang and the melon vendor must be playable');
  for (const row of ROSTER) {
    const character = CHARACTERS[row.id];
    assert.ok(Object.isFrozen(character), `${row.id} catalog record`);
    assert.match(row.id, /^[a-z][a-z0-9_-]*$/);
    assert.ok(Object.hasOwn(GROUPS, row.group), `${row.id} group`);
    assert.ok(Array.isArray(row.aliases) && row.aliases.every(alias => typeof alias === 'string' && alias.trim()), `${row.id} aliases`);
    assert.ok(row.sourceWork && row.sourceUrls.length && row.evidenceNote, `${row.id} needs research provenance`);
    for (const source of row.sourceUrls) assert.equal(new URL(source).protocol, 'https:', `${row.id} source`);
    assert.match(character.color, /^#[0-9a-f]{6}$/i);
    assert.ok(Number.isInteger(character.hp) && character.hp >= 100 && character.hp <= 116, `${row.id} life budget`);
    assert.ok(Number.isInteger(character.damage) && character.damage >= 30 && character.damage <= 40, `${row.id} damage budget`);
    assert.ok(Number.isInteger(character.drain) && character.drain >= 0 && character.drain <= 1, `${row.id} energy drain`);
    assert.equal(character.asset, originals.has(row.id) ? `/assets/${row.id}.glb` : `/assets/roster/${row.id}.glb`);
    assert.equal(character.motion, ROSTER_MOTIONS[row.id] || row.motion);
    if (!originals.has(row.id)) assert.ok(families.has(character.motion), `${row.id} reusable motion family`);
    assert.equal(newFighter('id', '玩家', row.id).character, row.id);
    assert.ok(row.appearance && row.weaponType && row.special, `${row.id} playable visual configuration`);
  }
  for (const invalid of ['__proto__', 'constructor', 'toString', '../huaqiang', '', null]) {
    assert.throws(() => newFighter('id', '玩家', invalid), /Unknown character/);
  }
});

test('model visuals, reusable motions, measured contacts and generated model files cover the same cast', async () => {
  const ids = ROSTER.filter(row => !originals.has(row.id)).map(row => row.id).sort();
  const assets = (await readdir(new URL('../public/assets/roster/', import.meta.url))).filter(name => name.endsWith('.glb')).map(name => name.slice(0, -4)).sort();
  assert.deepEqual(assets, ids, 'Generated model files must match the playable roster');
  for (const metadata of [ROSTER_VISUAL, ROSTER_MOTIONS, ROSTER_CONTACT]) assert.deepEqual(Object.keys(metadata).sort(), ids);
  for (const row of ROSTER) {
    assert.equal(CHARACTERS[row.id].weaponType, row.weaponType, `${row.id} research weapon classification is preserved`);
    if (originals.has(row.id)) continue;
    const visual = CHARACTERS[row.id].visual;
    assert.equal(visual, ROSTER_VISUAL[row.id]);
    assert.ok(visual.weaponType && visual.outfit && visual.hair && visual.build, `${row.id} actual model details`);
    for (const color of ['bodyColor', 'trimColor', 'hairColor', 'skinColor']) assert.match(visual[color], /^#[0-9a-f]{6}$/i, `${row.id} ${color}`);
  }
  assert.equal(CHARACTERS.huaqiang.visual.weaponType, 'knife');
  assert.equal(CHARACTERS.guatan.visual.weaponType, 'melon');
  assert.equal(CHARACTERS.yanshuangying.visual.weaponType, 'dualgun');
});

test('all added characters have authored appearance references and matching runtime colors', async () => {
  const profiles = JSON.parse(await readFile(new URL('../art/character-profiles.json', import.meta.url), 'utf8'));
  const ids = ROSTER.filter(row => !originals.has(row.id)).map(row => row.id).sort();
  assert.deepEqual(Object.keys(profiles).sort(), ids);
  for (const id of ids) {
    const profile = profiles[id];
    assert.ok(profile.referenceUrls.length && profile.referenceCue && profile.inferred, `${id} appearance provenance`);
    assert.ok(Object.values(profile.faceParams).every(value => Number.isFinite(value) && value > .5 && value < 1.5), `${id} face proportions`);
    assert.equal(CHARACTERS[id].visual.colorSpace, 'srgb', `${id} model and first-person colors agree`);
    assert.equal(CHARACTERS[id].visual.temperament, profile.temperament);
  }
});

test('the original three fighters retain their balance and every new move has finite contact data', () => {
  assert.deepEqual(['ikun', 'wang', 'lubu'].map(id => [CHARACTERS[id].hp, CHARACTERS[id].damage, CHARACTERS[id].drain]), [
    [108, 34, 0], [116, 30, 1], [100, 40, 0],
  ]);
  for (const id of Object.keys(CHARACTERS)) {
    if (originals.has(id)) continue;
    for (const action of ['strike', 'heavy', 'special']) {
      const contact = ROSTER_CONTACT[id]?.[action];
      assert.ok(Array.isArray(contact) && contact.length === 3 && contact.every(Number.isFinite), `${id} ${action} contact`);
    }
  }
});
