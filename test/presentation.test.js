import test from 'node:test';
import assert from 'node:assert/strict';
import { attackEnvelope, dampedSpring, opponentApproach, presentationTime, WEAPON_CONTACT } from '../shared/presentation.js';
import { TIMING } from '../shared/catalog.js';

test('every attack contacts at the server hit, has anticipation and recovers by the slot boundary', () => {
  for (const action of ['strike', 'heavy', 'special']) {
    assert.equal(attackEnvelope(0, action).extension, 0);
    assert.equal(attackEnvelope(300, action).windup, 1);
    assert.ok(attackEnvelope(550, action).extension < .5);
    assert.equal(attackEnvelope(TIMING.impact, action).extension, 1);
    assert.equal(attackEnvelope(TIMING.impact, action).windup, 0);
    assert.deepEqual(attackEnvelope(TIMING.slot, action), { windup: 0, extension: 0, follow: 0, guard: 0 });
  }
});

test('hit stop freezes contact for its whole interval without delaying the next server slot', () => {
  const hold = 80;
  assert.equal(presentationTime(TIMING.impact - 1, hold), TIMING.impact - 1);
  for (let ms = TIMING.impact; ms <= TIMING.impact + hold; ms++) {
    assert.equal(presentationTime(ms, hold), TIMING.impact);
    assert.equal(attackEnvelope(presentationTime(ms, hold)).extension, 1);
  }
  assert.ok(presentationTime(TIMING.impact + hold + 1, hold) > TIMING.impact);
  assert.equal(presentationTime(TIMING.slot, hold), TIMING.slot);
  assert.equal(presentationTime(TIMING.slot + 100, hold), TIMING.slot);
});

test('camera recovery is identical at 30, 60 and 144 fps and settles without oscillation', () => {
  const results = [30, 60, 144].map(fps => {
    let state = { position: .09, velocity: .35 };
    for (let frame = 0; frame < fps; frame++) state = dampedSpring(state.position, state.velocity, 1 / fps);
    return state;
  });
  assert.ok(Math.abs(results[0].position - results[2].position) < 1e-12);
  assert.ok(Math.abs(results[1].velocity - results[2].velocity) < 1e-12);
  assert.ok(results.every(state => Math.abs(state.position) < 1e-7));
  let state = { position: .1, velocity: 0 };
  for (let frame = 0; frame < 180; frame++) {
    state = dampedSpring(state.position, state.velocity, 1 / 60);
    assert.ok(state.position >= 0, 'critically damped kick must not oscillate');
  }
});

test('guard is raised before contact and held through the attack recovery', () => {
  assert.equal(attackEnvelope(200, 'guard').guard, 1);
  assert.equal(attackEnvelope(TIMING.impact, 'guard').guard, 1);
  assert.equal(attackEnvelope(1050, 'guard').guard, 1);
  assert.equal(attackEnvelope(TIMING.slot, 'guard').guard, 0);
});

test('all measured weapon contacts stay in front of the camera and blocked tips meet the raised guard', () => {
  for (const [character, actions] of Object.entries(WEAPON_CONTACT)) {
    for (const [action, point] of Object.entries(actions)) {
      const reach = opponentApproach(character, action);
      const contactZ = -1.8 + reach + point[2];
      assert.ok(3.4 - contactZ >= .3, `${character} ${action} must not pierce the camera`);
      assert.ok(Math.abs(point[0]) <= .35, `${character} ${action} must contact inside the opponent silhouette`);
      const visibleHalfHeight = (3.4 - contactZ) * Math.tan(55 * Math.PI / 360);
      assert.ok(Math.abs(point[1] - 1.72) <= visibleHalfHeight, `${character} ${action} contact must stay vertically visible`);
      assert.ok(Math.abs(point[0]) <= visibleHalfHeight * 4 / 3, `${character} ${action} contact must stay horizontally visible`);
      const blockedReach = opponentApproach(character, action, true);
      assert.ok(blockedReach <= reach);
      assert.ok(-1.8 + blockedReach + point[2] <= 2.560001, 'blocked weapons must stop outside the forearms');
    }
  }
});
