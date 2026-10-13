export const CHARACTERS = Object.freeze({
  ikun: {
    name: 'IKUN', subtitle: '节奏练习生', color: '#a89dff', hp: 108,
    weapon: '篮球', special: '节奏暴扣', damage: 34,
    description: '银发、背带与篮球。用一记暴扣，把节奏打进对手的回合。',
    quote: '下一回合，轮到我的主场。',
  },
  wang: {
    name: '王司徒', subtitle: '语言艺术家', color: '#6edbc9', hp: 116,
    weapon: '羽扇', special: '言语破防', damage: 30,
    description: '羽扇一挥，话锋比拳锋更快。绝招额外消耗对手 1 点气势。',
    quote: '且听老夫一言。',
  },
  lubu: {
    name: '吕布', subtitle: '无双猛将', color: '#ff896d', hp: 100,
    weapon: '方天画戟', special: '天下无双', damage: 40,
    description: '赤甲、双翎与画戟。生命略低，但绝招拥有最强的爆发。',
    quote: '这一戟，谁敢接？',
  },
});

export const ACTIONS = Object.freeze({
  strike: { name: '快攻', label: '蓄势一击', cost: 0, damage: 18, gain: 1, key: '1', detail: '造成 18 伤害 · 获得 1 气势' },
  heavy: { name: '重击', label: '强势破防', cost: 1, damage: 30, gain: 0, key: '2', detail: '造成 30 伤害 · 穿透大部分格挡' },
  guard: { name: '格挡', label: '稳住节奏', cost: 0, damage: 0, gain: 1, key: '3', detail: '减少 70% 普通伤害 · 获得 1 气势' },
  special: { name: '绝招', label: '明星时刻', cost: 2, damage: 0, gain: 0, key: '4', detail: '消耗 2 气势 · 释放角色专属招式' },
});

export const MAX_ENERGY = 3;
export const TIMING = Object.freeze({ plan: 8000, lead: 300, slot: 1450, impact: 620, rest: 600, roundBreak: 3200 });
export const EXECUTION_MS = TIMING.lead + TIMING.slot * 2 + TIMING.rest;
