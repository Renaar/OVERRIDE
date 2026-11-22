// Movement library for figure.js. Side view faces right (+x); ground at y = 110.
// A pose: hip [x,y], t = torso angle (deg from vertical, + leans toward +x), f1/f2 feet, h1/h2 hands
// (1 = near limb, 2 = far limb), kb/eb = knee/elbow bend side (+1 / -1), hd = head angle offset,
// arch = torso curvature. Keys of 2 poses play A -> B -> A with tempo [down, holdB, up, holdA] in s.
const R = Math.PI / 180;
const cos = (d) => Math.cos(d * R), sin = (d) => Math.sin(d * R);

// Straight body from the feet at angle phi above the horizontal (planks, push-ups).
const S = (fx, fy, phi, len = 50) => ({ hip: [fx + len * cos(phi), fy - len * sin(phi)], t: 90 - phi });
// Shoulder of a pose, and a hand/foot at `len` from it at angle `a` (0 = straight down, + toward +x).
const sh = (p) => [p.hip[0] + 32 * sin(p.t || 0), p.hip[1] - 32 * cos(p.t || 0)];
const reach = (o, a, len = 34) => [o[0] + len * sin(a), o[1] + len * cos(a)];

const STAND = { hip: [80, 60], t: 0, f1: [82, 110], f2: [78, 110], h1: [82, 94], h2: [78, 94] };
const SUPINE = { hip: [62, 104], t: 90, f1: [40, 110], f2: [38, 110], kb: -1, h1: [64, 108], h2: [62, 108], eb: 1 };
const HANG_BOX = { box: "0 0 160 135", ground: false };

// ---------------------------------------------------------------- push
const pushTop = { ...S(40, 110, 24.5), f1: [40, 110], h1: [114.6, 111.5] };
const pushBot = { ...S(40, 110, 7), f1: [40, 110], h1: [115, 110] };
const inclTop = { ...S(40, 110, 42), f1: [40, 110], h1: [124.4, 81] };
const inclBot = { ...S(40, 110, 26), f1: [40, 110], h1: [124, 80] };
const declTop = { ...S(30, 65, -7.7), f1: [30, 65], h1: [111.3, 111.5] };
const declBot = { ...S(30, 65, -25.3), f1: [30, 65], h1: [111, 110] };
const defTop = { ...S(40, 110, 30.8), f1: [40, 110], h1: [110.4, 103.5] };
const defBot = { ...S(40, 110, 2.8), f1: [40, 110], h1: [110, 102] };
const floorPress = (top) => ({ ...SUPINE, h1: top ? [94, 68] : [78, 88], h2: top ? [94, 68] : [78, 88], eb: 1 });
const benchPress = (top) => ({ ...floorPress(top), hip: [62, 92], f1: [32, 110], f2: [30, 110], h1: top ? [94, 56] : [80, 80], h2: top ? [94, 56] : [80, 80] });

// ---------------------------------------------------------------- pull
const rowBase = { hip: [66, 60], t: 90, f1: [62, 110], f2: [42, 82], kb2: 1, h2: [104, 82] };
const rowDown = { ...rowBase, h1: [100, 94] };
const rowUp = { ...rowBase, h1: [86, 66] };
const incl = { hip: [70, 72], t: 45, f1: [56, 110], f2: [54, 110] };
const hangDown = { hip: [80, 81], t: 0, shrug: 4, f1: [80, 130], f2: [78, 130], h1: [80, 9], h2: [80, 9] };
const hangActive = { ...hangDown, hip: [80, 77], shrug: 0, f1: [80, 126], f2: [78, 126] };
const hangUp = { ...hangActive, hip: [80, 58], f1: [76, 104], f2: [74, 104] };
const bar = [{ l: [50, 10, 110, 10] }, { c: [50, 10, 1.5] }, { c: [110, 10, 1.5] }];
const board = [{ r: [56, 2, 48, 7] }];

// ---------------------------------------------------------------- legs
const gobletUp = { ...STAND, hip: [78, 60], h1: [88, 42], h2: [86, 42] };
const gobletDown = { hip: [64, 90], t: 35, f1: [82, 110], f2: [78, 110], h1: [94, 70], h2: [92, 70] };
const gobletHalf = { hip: [72, 76], t: 20, f1: [82, 110], f2: [78, 110], h1: [92, 56], h2: [90, 56] };
const bwUp = { ...STAND, h1: [114, 36], h2: [112, 36] };
const bwDown = { ...gobletDown, h1: [118, 62], h2: [116, 62] };
const lungeUp = { ...STAND, f1: [84, 110], f2: [80, 110] };
const lungeDown = { hip: [64, 84], t: 4, f1: [84, 110], f2: [38, 108], h1: [68, 116], h2: [66, 116] };
const bulgUp = { hip: [70, 62], t: 6, f1: [84, 110], f2: [36, 80], h1: [74, 96], h2: [72, 96] };
const bulgDown = { hip: [66, 86], t: 10, f1: [84, 110], f2: [36, 80], h1: [72, 118], h2: [70, 118] };
const bridgeDown = { ...SUPINE, h1: [58, 107], h2: [58, 107] };
const bridgeUp = { ...bridgeDown, hip: [65.7, 89], t: 118, hd: -28 };
const thrustDown = { hip: [76.6, 97.8], t: 47, hd: -20, f1: [50, 110], f2: [48, 110], kb: -1, h1: [134, 77], h2: [134, 77], eb: 1 };
const thrustUp = { ...thrustDown, hip: [68, 76], t: 90, hd: -10 };
const rdlUp = { ...STAND, h1: [84, 94], h2: [82, 94] };
const rdlDown = { hip: [62, 63], t: 72, f1: [82, 110], f2: [78, 110], h1: [90, 92], h2: [88, 92] };

// ---------------------------------------------------------------- core
const plank = { ...S(30.5, 110, 14.1), f1: [30.5, 110], h1: [127, 108] };
const plankExt = { ...S(28, 110, 12.7), f1: [28, 110], h1: [137, 108] };
const tabletop = { hip: [62, 104], t: 90, f1: [37, 79], f2: [37, 79], kb: -1, h1: [94, 69], h2: [94, 69] };
const quad = { hip: [60, 85], t: 72, f1: [35, 108], f2: [35, 108], h1: [91, 110], h2: [91, 110] };
const side = { ...S(30, 110, 13.4), hw: 0, sw: 0, f1: [31, 104], f2: [30, 110], h1: [110, 54], h2: [110, 110], fore2: 0.08 };
const sideKnee = { ...S(55, 110, 19.5, 25), hw: 0, sw: 0, f1: [53, 104], f2: [53, 111], shin1: 0.1, shin2: 0.1, h1: [109, 54], h2: [109, 110], fore2: 0.08 };
const copKnee = { hip: [68.6, 84.3], t: 100, hw: 0, sw: 0, f1: [26, 79], f2: [58, 109], h1: [100, 54], h2: [100, 110], fore2: 0.08 };
const copStraight = { hip: [77.5, 85.7], t: 97.7, hw: 0, sw: 0, f1: [27, 78], f2: [66, 109], h1: [109, 54], h2: [109, 110], fore2: 0.08 };

// ---------------------------------------------------------------- carry
const walk = (p, a) => ({ ...STAND, ...p, hip: [80, a ? 58 : 60] });
const walkKeys = (hands) => [
  walk({ f1: [92, 110], f2: [68, 110], ...hands }, 0),
  walk({ f1: [80, 110], f2: [84, 102], ...hands }, 1),
  walk({ f1: [68, 110], f2: [92, 110], ...hands }, 0),
  walk({ f1: [84, 102], f2: [80, 110], ...hands }, 1),
];

// ---------------------------------------------------------------- mobility
const deepSquat = { hip: [66, 92], t: 28, f1: [82, 110], f2: [78, 110], h1: [92, 82], h2: [90, 82] };
const cossack = (left) => left
  ? { hip: [58, 96], t: -6, hw: 6, sw: 10, f1: [40, 110], f2: [112, 110], kb1: -1, kb2: 1, h1: [76, 66], h2: [84, 66] }
  : { hip: [102, 96], t: 6, hw: 6, sw: 10, f1: [48, 110], f2: [120, 110], kb1: -1, kb2: 1, h1: [96, 66], h2: [104, 66] };
const frontStand = { hip: [80, 60], t: 0, hw: 6, sw: 10, f1: [74, 110], f2: [86, 110], h1: [68, 94], h2: [92, 94], eb1: 1, eb2: -1 };
const breath = (inhale) => ({ ...SUPINE, h1: [78, inhale ? 97 : 100], h2: [76, inhale ? 97 : 100], eb: 1 });
const prone = (inhale) => ({ hip: [60, inhale ? 102 : 104], t: 90, f1: [10, 108], f2: [10, 108], h1: [126, 108], h2: [126, 108], eb: 1, hd: 4 });

export const FIGURES = {
  // push
  pushup: { label: "Pompe", k: [pushTop, pushBot] },
  pushup_incline: { label: "Pompe mains surélevées", props: [{ r: [120, 80, 34, 30] }], k: [inclTop, inclBot] },
  pushup_decline: { label: "Pompe pieds surélevés", props: [{ r: [14, 65, 26, 45] }], k: [declTop, declBot] },
  pushup_deficit: { label: "Pompe en déficit", props: [{ r: [104, 102, 13, 8] }], k: [defTop, defBot] },
  floor_press: { label: "Développé au sol", db: ["h1"], k: [floorPress(false), floorPress(true)] },
  bench_press: { label: "Développé couché", db: ["h1"], props: [{ r: [44, 96, 60, 5] }, { l: [52, 101, 52, 110] }, { l: [96, 101, 96, 110] }], k: [benchPress(false), benchPress(true)] },
  pike: { label: "Pompe pike", toes: true,
    k: [{ hip: [80, 60], t: 135, f1: [66, 110], f2: [64, 110], h1: [118, 110] }, { hip: [82, 63], t: 155, f1: [66, 110], f2: [64, 110], h1: [118, 110] }] },
  pike_decline: { label: "Pompe pike pieds surélevés", props: [{ r: [30, 62, 24, 48] }],
    k: [{ hip: [88, 46], t: 170, f1: [40, 62], f2: [40, 62], h1: [99, 110] }, { hip: [92, 56], t: 178, f1: [40, 62], f2: [40, 62], h1: [99, 110] }] },
  ohp_seated: { label: "Développé épaules assis", db: ["h1"], props: [{ r: [58, 85, 30, 25] }, { l: [62, 85, 62, 45] }],
    k: [{ hip: [75, 83], t: 0, f1: [101, 110], f2: [99, 110], h1: [79, 44], h2: [77, 44] }, { hip: [75, 83], t: 0, f1: [101, 110], f2: [99, 110], h1: [77, 17], h2: [75, 17] }] },
  overhead_ext: { label: "Extension triceps", box: "0 -14 160 134", db: ["h1"], toes: true,
    k: [{ ...STAND, h1: [72, 18], h2: [72, 18] }, { ...STAND, h1: [80, -6], h2: [80, -6] }] },
  skullcrusher: { label: "Extension allongé", db: ["h1"], k: [{ ...SUPINE, h1: [94, 69], eb: 1 }, { ...SUPINE, h1: [108, 92], eb: 1 }] },
  lateral_raise: { label: "Élévations latérales", view: "front", db: ["h1", "h2"], dbAngle: 90,
    k: [frontStand, { ...frontStand, h1: [37, 34], h2: [123, 34] }] },

  // pull
  row: { label: "Rowing un bras", db: ["h1"], props: [{ r: [36, 82, 74, 6] }, { l: [42, 88, 42, 110] }, { l: [104, 88, 104, 110] }], k: [rowDown, rowUp], tempo: [0.9, 0.4, 1.3, 0.4] },
  row_bw: { label: "Rowing à vide", props: [{ r: [36, 82, 74, 6] }, { l: [42, 88, 42, 110] }, { l: [104, 88, 104, 110] }], k: [rowDown, rowUp] },
  row_incline: { label: "Rowing appui poitrine", db: ["h1"], props: [{ l: [74, 77, 100, 51] }, { l: [84, 67, 84, 110] }],
    k: [{ ...incl, h1: [96, 86], h2: [94, 86] }, { ...incl, h1: [84, 62], h2: [82, 62] }] },
  band_row: { label: "Tirage élastique", band: [[152, 44], "h1"], toes: true,
    k: [{ ...STAND, hip: [80, 61], h1: [113, 42], h2: [111, 42] }, { ...STAND, hip: [80, 61], h1: [90, 48], h2: [88, 48] }] },
  pullover: { label: "Pullover", db: ["h1"], k: [{ ...SUPINE, h1: [94, 69], eb: 1 }, { ...SUPINE, h1: [126, 96], eb: 1 }] },
  scap_pull: { label: "Élévations scapulaires", ...HANG_BOX, props: board, k: [hangDown, hangActive], tempo: [0.9, 0.8, 1.2, 0.5] },
  pullup: { label: "Traction", ...HANG_BOX, props: bar, k: [hangActive, hangUp] },
  pullup_negative: { label: "Traction négative", ...HANG_BOX, props: bar, k: [hangUp, hangActive], tempo: [4, 0.4, 0.8, 0.6] },
  pullup_assisted: { label: "Traction assistée", ...HANG_BOX, props: bar, band: [[80, 10], "f1"], k: [hangActive, hangUp] },
  hang: { label: "Suspension", ...HANG_BOX, props: board, k: [hangDown] },
  hang_active: { label: "Suspension active", ...HANG_BOX, props: board, k: [hangActive] },
  hang_feet: { label: "Suspension pieds au sol", box: "0 0 160 135", gy: 124, props: board, k: [{ ...hangDown, f1: [98, 124], f2: [96, 124] }] },
  curl: { label: "Curl", db: ["h1", "h2"], toes: true, k: [{ ...STAND, h1: [82, 62], h2: [80, 62] }, { ...STAND, h1: [88, 36], h2: [86, 36] }] },
  curl_hammer: { label: "Curl marteau", db: ["h1", "h2"], dbAngle: 90, toes: true, k: [{ ...STAND, h1: [82, 62], h2: [80, 62] }, { ...STAND, h1: [88, 36], h2: [86, 36] }] },
  curl_incline: { label: "Curl incliné", db: ["h1"], props: [{ l: [66, 92, 44, 58] }, { l: [56, 86, 56, 110] }],
    k: [{ hip: [70, 84], t: -35, f1: [100, 110], f2: [98, 110], h1: [52, 92] }, { hip: [70, 84], t: -35, f1: [100, 110], f2: [98, 110], h1: [62, 60] }] },

  // legs
  goblet: { label: "Squat gobelet", db: ["h1"], dbAngle: 90, toes: true, k: [gobletUp, gobletDown] },
  goblet_15: { label: "Squat 1,5", db: ["h1"], dbAngle: 90, toes: true, k: [gobletUp, gobletDown, gobletHalf, gobletDown], step: 0.9, hold: 0.15 },
  squat_bw: { label: "Squat au poids du corps", toes: true, k: [bwUp, bwDown], tempo: [1.6, 0.3, 1.4, 0.4] },
  pistol_box: { label: "Squat sur un pied", toes: true, props: [{ r: [40, 82, 28, 28] }],
    k: [{ hip: [78, 60], t: 6, f1: [82, 110], f2: [104, 92], h1: [112, 42], h2: [110, 42] }, { hip: [58, 80], t: 26, f1: [82, 110], f2: [106, 72], h1: [110, 56], h2: [108, 56] }] },
  lunge: { label: "Fente arrière", toes: true, k: [lungeUp, lungeDown] },
  lunge_db: { label: "Fente arrière haltères", db: ["h1"], toes: true, k: [{ ...lungeUp, h1: [82, 94] }, { ...lungeDown, h1: [68, 96] }] },
  bulgarian: { label: "Squat bulgare", db: ["h1"], toes: true, props: [{ r: [20, 82, 28, 28] }], k: [bulgUp, bulgDown] },
  bulgarian_deficit: { label: "Squat bulgare en déficit", db: ["h1"], props: [{ r: [20, 82, 28, 28] }, { r: [74, 104, 22, 6] }],
    k: [{ ...bulgUp, f1: [84, 104], hip: [70, 57] }, { ...bulgDown, f1: [84, 104], hip: [64, 84] }] },
  bridge: { label: "Pont fessier", db: ["hip"], k: [bridgeDown, bridgeUp] },
  bridge_bw: { label: "Pont fessier", k: [bridgeDown, bridgeUp] },
  hip_thrust: { label: "Hip thrust", db: ["hip"], props: [{ r: [98, 78, 46, 32] }], k: [thrustDown, thrustUp] },
  hip_thrust_sl: { label: "Hip thrust une jambe", db: ["hip"], props: [{ r: [98, 78, 46, 32] }],
    k: [{ ...thrustDown, f2: [36, 82] }, { ...thrustUp, f2: [18, 76] }] },
  rdl: { label: "Soulevé de terre roumain", db: ["h1"], toes: true, k: [rdlUp, rdlDown], tempo: [3, 0.3, 1, 0.5] },
  rdl_sl: { label: "Roumain une jambe", db: ["h1"], toes: true,
    k: [{ ...rdlUp, f2: [76, 104] }, { ...rdlDown, f2: [15, 79] }], tempo: [2.2, 0.4, 1.2, 0.5] },
  calf: { label: "Mollets", db: ["h1"], toes: 100, props: [{ r: [76, 100, 34, 10] }],
    k: [{ ...STAND, hip: [80, 53], f1: [80, 103], f2: [66, 92], h1: [82, 87] }, { ...STAND, hip: [80, 44], f1: [80, 94], f2: [66, 83], h1: [82, 78] }] },

  // core
  plank: { label: "Planche", k: [plank] },
  plank_ext: { label: "Planche bras avancés", k: [plankExt] },
  mcgill: { label: "Curl-up McGill", k: [{ ...SUPINE, f1: [12, 108], f2: [40, 110], kb2: -1, h1: [70, 106], h2: [70, 106] }, { ...SUPINE, t: 84, f1: [12, 108], f2: [40, 110], kb2: -1, h1: [70, 106], h2: [70, 106] }], tempo: [0.8, 2.5, 0.8, 1] },
  dead_bug: { label: "Dead bug", k: [tabletop, { ...tabletop, h1: [127, 98], f2: [13, 100] }], tempo: [1.4, 0.4, 1.2, 0.5] },
  dead_bug_db: { label: "Dead bug haltère", db: ["h1"], k: [tabletop, { ...tabletop, f1: [13, 100] }], tempo: [1.4, 0.4, 1.2, 0.5] },
  side_plank: { label: "Planche latérale", view: "front", k: [side] },
  side_plank_knees: { label: "Planche latérale genoux", view: "front", k: [sideKnee] },
  side_plank_leg: { label: "Planche latérale jambe levée", view: "front", k: [side, { ...side, f1: [32, 86] }], tempo: [1, 1.5, 1, 0.8] },
  copenhagen_knee: { label: "Copenhague genou", view: "front", props: [{ r: [10, 80, 34, 30] }], k: [copKnee] },
  copenhagen: { label: "Copenhague jambe tendue", view: "front", props: [{ r: [10, 80, 30, 30] }], k: [copStraight] },
  bird_dog: { label: "Bird-dog", k: [quad, { ...quad, h1: [126, 74], f2: [10, 85] }], tempo: [1.2, 0.8, 1.2, 0.6] },
  bird_dog_pause: { label: "Bird-dog pause", k: [quad, { ...quad, h1: [126, 74], f2: [10, 85] }], tempo: [1.4, 3, 1.4, 0.6] },
  shoulder_tap: { label: "Touches d'épaule", k: [pushTop, { ...pushTop, h1: [110, 80] }], tempo: [0.6, 0.3, 0.6, 0.6] },
  renegade: { label: "Renegade row", db: ["h1", "h2"], props: [], k: [defTop, { ...defTop, h1: [98, 90] }], tempo: [1, 0.4, 1.4, 0.6] },
  farmer: { label: "Marche du fermier", db: ["h1", "h2"], dbAngle: 0, toes: true, k: walkKeys({ h1: [80, 94], h2: [80, 94] }), step: 0.4, hold: 0 },
  suitcase: { label: "Marche valise", db: ["h1"], toes: true, k: walkKeys({ h1: [80, 94], h2: [80, 94] }), step: 0.4, hold: 0 },
  overhead_carry: { label: "Marche bras tendu", box: "0 -14 160 134", db: ["h1"], toes: true, k: walkKeys({ h1: [82, -6], h2: [80, 94] }), step: 0.4, hold: 0 },

  // isometrics
  iso_pushup: { label: "Tenue pompe", k: [{ ...S(40, 110, 12), f1: [40, 110], h1: [115, 110] }] },
  iso_curl: { label: "Tenue curl", db: ["h1", "h2"], toes: true, k: [{ ...STAND, h1: [97, 46], h2: [95, 46] }] },
  iso_lateral: { label: "Tenue élévation latérale", view: "front", db: ["h1", "h2"], dbAngle: 90, k: [{ ...frontStand, h1: [37, 34], h2: [123, 34] }] },
  wall_sit: { label: "Chaise", props: [{ l: [50, 14, 50, 110] }], toes: true, k: [{ hip: [56, 85], t: 0, f1: [82, 110], f2: [80, 110], h1: [76, 84], h2: [74, 84] }] },
  bridge_hold: { label: "Pont tenu", db: ["hip"], k: [bridgeUp] },

  // mobility
  low_lunge: { label: "Fente basse", toes: true, k: [{ hip: [70, 83], t: 0, f1: [96, 110], f2: [34, 108], h1: [92, 80], h2: [90, 80] }, { hip: [76, 86], t: -4, f1: [96, 110], f2: [34, 108], h1: [94, 82], h2: [92, 82] }], tempo: [2, 1.2, 2, 0.8] },
  deep_squat: { label: "Accroupi profond", toes: true, k: [deepSquat] },
  deep_squat_db: { label: "Accroupi profond haltère", db: ["h1"], dbAngle: 90, toes: true, k: [{ ...deepSquat, h1: [92, 70], h2: [90, 70] }] },
  cossack: { label: "Squat cosaque", view: "front", k: [cossack(true), cossack(false)], tempo: [1.8, 0.6, 1.8, 0.6] },
  cat_cow: { label: "Chat-vache", k: [{ ...quad, arch: -9, hd: 35 }, { ...quad, arch: 7, hd: -30 }], tempo: [2, 0.6, 2, 0.6] },
  thoracic_rotation: { label: "Rotation thoracique", k: [{ ...quad, h1: [86, 104], eb1: 1 }, { ...quad, h1: [94, 42] }], tempo: [1.6, 0.8, 1.6, 0.4] },
  wall_slides: { label: "Glissés au mur", view: "front", box: "0 -14 160 134", toes: false,
    k: [{ ...frontStand, h1: [54, 12], h2: [106, 12], eb1: 1, eb2: -1 }, { ...frontStand, h1: [64, -5], h2: [96, -5], eb1: 1, eb2: -1 }], tempo: [1.8, 0.4, 1.8, 0.4] },
  dislocates: { label: "Passages d'épaules", box: "0 -14 160 134", toes: true,
    k: [{ ...STAND, h1: reach([80, 28], 35, 35), h2: reach([80, 28], 35, 35) }, { ...STAND, h1: [80, -7], h2: [80, -7] },
      { ...STAND, h1: reach([80, 28], -35, 35), h2: reach([80, 28], -35, 35) }, { ...STAND, h1: [80, -7], h2: [80, -7] }], step: 1, hold: 0.2 },
  knee_wall: { label: "Genou au mur", props: [{ l: [120, 14, 120, 110] }], toes: true,
    k: [{ hip: [76, 64], t: 4, f1: [104, 110], f2: [56, 110], h1: [118, 44], h2: [118, 44] }, { hip: [86, 70], t: 8, f1: [104, 110], f2: [56, 110], h1: [118, 46], h2: [118, 46] }], tempo: [1.5, 1, 1.5, 0.6] },
  ham_chair: { label: "Étirement ischios", props: [{ r: [104, 80, 26, 30] }],
    k: [{ hip: [70, 61], t: 0, f1: [121, 78], f2: [66, 110], h1: [78, 62], h2: [76, 62] }, { hip: [66, 62], t: 42, f1: [117, 78], f2: [66, 110], h1: [100, 74], h2: [98, 74] }], tempo: [2.2, 1.5, 2, 0.6] },

  // warm-up & breathing
  arm_circles: { label: "Cercles de bras", view: "front",
    k: [[0, -6], [6, 0], [0, 6], [-6, 0]].map(([dx, dy]) => ({ ...frontStand, h1: [37 + dx, 32 + dy], h2: [123 - dx, 32 + dy] })), step: 0.25, hold: 0 },
  scap_pushup: { label: "Pompes scapulaires", k: [pushTop, { ...S(40, 110, 22.5), f1: [40, 110], h1: [115, 110] }], tempo: [0.8, 0.3, 0.8, 0.3] },
  torso_rotation: { label: "Rotations du buste", view: "front", k: [{ ...frontStand, h1: [56, 48], h2: [58, 46] }, { ...frontStand, h1: [102, 46], h2: [104, 48] }], tempo: [1, 0.2, 1, 0.2] },
  hip_circles: { label: "Cercles de hanches", view: "front",
    k: [[-6, 0], [0, 2], [6, 0], [0, -2]].map(([dx, dy]) => ({ ...frontStand, hip: [80 + dx, 60 + dy], h1: [72 + dx, 62 + dy], h2: [88 + dx, 62 + dy] })), step: 0.5, hold: 0 },
  breathing: { label: "Respiration", k: [breath(false), breath(true)], tempo: [4, 0.5, 6, 0.5] },
  crocodile: { label: "Respiration crocodile", k: [prone(false), prone(true)], tempo: [4, 0.5, 6, 0.5] },
};
