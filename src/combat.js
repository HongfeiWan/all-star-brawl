import { ACTIONS, CHARACTERS, MAX_ENERGY, TIMING } from '../shared/catalog.js';

export function newFighter(id, name, character, bot = false) {
  if (!Object.hasOwn(CHARACTERS, character)) throw new Error('Unknown character');
  return { id, name, character, bot, hp: CHARACTERS[character].hp, energy: 1, wins: 0, locked: false, choice: null };
}

export function resetRound(players) {
  for (const p of players) {
    p.hp = CHARACTERS[p.character].hp;
    p.energy = 1;
    p.locked = false;
    p.choice = null;
  }
}

export function canChoose(player, action) {
  return Object.hasOwn(ACTIONS, action) && player.energy >= ACTIONS[action].cost;
}

// Both commitments are resolved from the same starting state; a KO never cancels the other attack.
export function resolveTurn(players, turn) {
  if (players.length !== 2) throw new Error('A duel needs two fighters');
  const choices = players.map(p => canChoose(p, p.choice) ? p.choice : 'guard');
  const damage = [0, 0];
  const energy = players.map((p, i) => Math.min(MAX_ENERGY, p.energy - ACTIONS[choices[i]].cost + ACTIONS[choices[i]].gain));
  const order = turn % 2 ? [0, 1] : [1, 0];
  const events = order.map((index, slot) => {
    const target = 1 - index;
    const player = players[index];
    const action = choices[index];
    const defending = choices[target] === 'guard';
    const raw = action === 'special' ? CHARACTERS[player.character].damage : ACTIONS[action].damage;
    const amount = Math.round(raw * (defending ? (action === 'heavy' ? 0.8 : 0.3) : 1));
    damage[target] += amount;
    if (action === 'special') energy[target] = Math.max(0, energy[target] - (CHARACTERS[player.character].drain || 0));
    return {
      actor: player.id, target: players[target].id, action, damage: amount, blocked: defending && raw > 0,
      title: action === 'special' ? CHARACTERS[player.character].special : ACTIONS[action].name,
      start: TIMING.lead + slot * TIMING.slot, hit: TIMING.lead + slot * TIMING.slot + TIMING.impact,
    };
  });
  return { events, after: players.map((p, i) => ({ id: p.id, hp: Math.max(0, p.hp - damage[i]), energy: energy[i] })) };
}

export function roundWinner(players, turn) {
  if (players.every(p => p.hp > 0) && turn < 20) return undefined;
  const ratios = players.map(p => p.hp / CHARACTERS[p.character].hp);
  if (ratios[0] === ratios[1]) return null;
  return players[ratios[0] > ratios[1] ? 0 : 1].id;
}
