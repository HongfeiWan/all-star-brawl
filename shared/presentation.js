import { TIMING } from './catalog.js';

const clamp = value => Math.max(0, Math.min(1, value));
const ease = (from, to, value) => {
  const t = clamp((value - from) / (to - from));
  return t * t * (3 - 2 * t);
};

// Hold the exact contact pose, then finish recovery inside the authoritative slot.
export function presentationTime(elapsed, hold = 0) {
  if (elapsed <= TIMING.impact) return Math.max(0, elapsed);
  if (elapsed <= TIMING.impact + hold) return TIMING.impact;
  const recovery = TIMING.slot - TIMING.impact;
  return Math.min(TIMING.slot, TIMING.impact + (elapsed - TIMING.impact - hold) * recovery / (recovery - hold));
}

export function attackEnvelope(elapsed, action = 'strike') {
  const t = Math.max(0, elapsed);
  if (t >= TIMING.slot) return { windup: 0, extension: 0, follow: 0, guard: 0 };
  if (action === 'guard') {
    return { windup: 0, extension: 0, follow: 0, guard: ease(0, 180, t) * (1 - ease(1080, 1400, t)) };
  }
  const release = action === 'strike' ? 365 : 445;
  const windup = ease(0, 290, t) * (1 - ease(release, TIMING.impact, t));
  const extension = t <= TIMING.impact
    ? clamp((t - release) / (TIMING.impact - release)) ** 3
    : 1 - ease(TIMING.impact + 55, 1320, t);
  const follow = ease(TIMING.impact, TIMING.impact + 150, t) * (1 - ease(800, 1300, t));
  return { windup, extension, follow, guard: 0 };
}

// Exact critically damped spring integration gives the same kick at any frame rate.
export function dampedSpring(position, velocity, dt, frequency = 19) {
  const decay = Math.exp(-frequency * dt);
  const term = velocity + frequency * position;
  return {
    position: (position + term * dt) * decay,
    velocity: (velocity - frequency * term * dt) * decay,
  };
}

// Measured from the skinned weapon tips at the exported 620 ms contact sample.
export const WEAPON_CONTACT = Object.freeze({
  ikun: { strike: [-.099, 1.423, .998], heavy: [.277, 1.377, .891], special: [-.131, 1.491, 1.014] },
  wang: { strike: [.272, 1.683, .738], heavy: [-.208, 1.850, .854], special: [.246, 1.521, .815] },
  lubu: { strike: [.038, 1.602, 2.218], heavy: [-.067, 1.611, 2.216], special: [-.319, 1.649, 1.632] },
});

export function opponentApproach(character, action, blocked = false) {
  const approach = character === 'lubu' ? action === 'special' ? 2.9 : 2.6 : character === 'wang' ? 3.35 : 3.5;
  const contact = WEAPON_CONTACT[character]?.[action];
  // A block meets foreground forearms at z 2.56 from the opponent's rest z -1.8.
  return blocked && contact ? Math.min(approach, 4.36 - contact[2]) : approach;
}
