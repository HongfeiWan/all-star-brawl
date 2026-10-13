import { ROSTER } from './roster.js';
import { ROSTER_MOTIONS, ROSTER_VISUAL } from './roster-contacts.js';
export { ROSTER, GROUPS } from './roster.js';

const originals = new Set(['ikun', 'wang', 'lubu']);
export const CHARACTERS = Object.freeze(Object.fromEntries(ROSTER.map(row => [row.id, Object.freeze({
  ...row,
  asset: originals.has(row.id) ? `/assets/${row.id}.glb` : `/assets/roster/${row.id}.glb`,
  motion: ROSTER_MOTIONS[row.id] || row.motion,
  visual: ROSTER_VISUAL[row.id],
  drain: row.id === 'wang' ? 1 : (row.drain || 0),
})])));

export const ACTIONS = Object.freeze({
  strike: { name: '快攻', label: '蓄势一击', cost: 0, damage: 18, gain: 1, key: '1', detail: '造成 18 伤害 · 获得 1 气势' },
  heavy: { name: '重击', label: '强势破防', cost: 1, damage: 30, gain: 0, key: '2', detail: '造成 30 伤害 · 穿透大部分格挡' },
  guard: { name: '格挡', label: '稳住节奏', cost: 0, damage: 0, gain: 1, key: '3', detail: '减少 70% 普通伤害 · 获得 1 气势' },
  special: { name: '绝招', label: '明星时刻', cost: 2, damage: 0, gain: 0, key: '4', detail: '消耗 2 气势 · 释放角色专属招式' },
});

export const MAX_ENERGY = 3;
export const TIMING = Object.freeze({ plan: 8000, lead: 300, slot: 1450, impact: 620, rest: 600, roundBreak: 3200 });
export const EXECUTION_MS = TIMING.lead + TIMING.slot * 2 + TIMING.rest;
