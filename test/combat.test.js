import test from 'node:test';
import assert from 'node:assert/strict';
import { newFighter, canChoose, resetRound, resolveTurn, roundWinner } from '../src/combat.js';
import { CHARACTERS, EXECUTION_MS } from '../shared/catalog.js';

const fighters = () => [newFighter('a', 'A', 'ikun'), newFighter('b', 'B', 'lubu')];
test('choices reject unknown actions and insufficient energy', () => {
  const [player] = fighters();
  assert.equal(canChoose(player, 'toString'), false);
  assert.equal(canChoose(player, 'special'), false);
  assert.equal(canChoose(player, 'strike'), true);
  assert.throws(() => newFighter('x', 'X', '__proto__'));
});
test('both attacks resolve even when both players are knocked out', () => {
  const players = fighters();
  players.forEach(p => { p.hp = 10; p.choice = 'strike'; });
  const outcome = resolveTurn(players, 1);
  assert.deepEqual(outcome.after.map(p => p.hp), [0, 0]);
  assert.deepEqual(players.map(p => p.hp), [10, 10]);
  outcome.after.forEach((after, i) => Object.assign(players[i], after));
  assert.equal(roundWinner(players, 1), null);
});
test('guard cuts ordinary damage while heavy strikes break most of the guard', () => {
  const players = fighters();
  players[1].choice = 'guard';
  players[0].choice = 'strike';
  assert.equal(resolveTurn(players, 1).events[0].damage, 5);
  players[0].choice = 'heavy';
  const outcome = resolveTurn(players, 1);
  assert.equal(outcome.events[0].damage, 24);
  assert.deepEqual(outcome.after.map(p => p.energy), [0, 2]);
});
test('Wang Situ drains energy and every special has its own damage', () => {
  for (const [id, character] of Object.entries(CHARACTERS)) {
    const players = [newFighter('a', 'A', id), newFighter('b', 'B', 'ikun')];
    players[0].energy = 3; players[0].choice = 'special'; players[1].choice = 'strike';
    const outcome = resolveTurn(players, 1);
    assert.equal(outcome.events[0].damage, character.damage);
    assert.equal(outcome.after[1].energy, id === 'wang' ? 1 : 2);
    assert.equal(outcome.after[0].energy, 1);
  }
});
test('timeout defaults to guard, energy is capped, and order alternates', () => {
  const players = fighters(); players.forEach(p => { p.energy = 3; });
  const outcome = resolveTurn(players, 2);
  assert.deepEqual(outcome.after.map(p => p.energy), [3, 3]);
  assert.deepEqual(outcome.events.map(e => e.actor), ['b', 'a']);
  assert.ok(outcome.events.every(e => e.hit < EXECUTION_MS));
  assert.equal(roundWinner(players, 19), undefined);
  assert.equal(roundWinner(players, 20), null);
  players[0].hp = 54; players[1].hp = 49;
  assert.equal(roundWinner(players, 20), 'a');
});
test('round resets preserve scores and identity', () => {
  const players = fighters(); players[0].wins = 1; players[0].hp = 0; players[0].energy = 0;
  resetRound(players);
  assert.equal(players[0].wins, 1);
  assert.equal(players[0].hp, 108);
  assert.equal(players[0].id, 'a');
});
