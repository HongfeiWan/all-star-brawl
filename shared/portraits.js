// Enable an entry only after its saved photograph and subject identity are verified.
// Framing is presentation metadata; the original local photograph remains intact.
export const PORTRAITS = {
  ikun: {
    available: true,
    src: '/assets/portraits/ikun.jpg',
    alt: '蔡徐坤 2018 年 COSMO 活动照片',
    sourceUrl: 'https://commons.wikimedia.org/wiki/File:Cai_Xukun_in_2018.jpg',
    sourceTitle: '蔡徐坤 2018 年本人照 · Rosethron · CC BY 2.5',
    width: 1152,
    height: 1728,
    crop: [395, 285, 470, 540],
    objectPosition: '50% 50%',
    scale: 1,
  },
  huaqiang: {
    available: true,
    src: '/assets/portraits/huaqiang-frontal.png',
    alt: '孙红雷饰演的刘华强，买瓜片段画面',
    sourceUrl: 'https://news.sina.cn/2019-07-16/detail-ihytcerm4065290.d.html',
    sourceTitle: '观察者网 / 新浪：买瓜偶遇本人保熟表情包',
    width: 240,
    height: 200,
    crop: [117, 0, 96, 158],
    objectPosition: '50% 50%',
    scale: 1,
  },
  guatan: {
    available: true,
    src: '/assets/portraits/guatan.png',
    alt: '李广奇饰演的瓜摊老板，征服片段画面',
    sourceUrl: 'https://www.sohu.com/a/489418830_100120160',
    sourceTitle: '搜狐：狠人李广奇，征服里卖瓜',
    width: 1402,
    height: 912,
    crop: [195, 0, 510, 590],
    objectPosition: '50% 50%',
    scale: 1,
  },
};

export function portraitFor(id) {
  const portrait = PORTRAITS[id];
  return portrait?.available && portrait.src && portrait.sourceUrl ? portrait : null;
}
