// BODY OS logic tests — run: node test-logic.js
const fs = require('fs');
let js = fs.readFileSync('/tmp/bodyos.js', 'utf8');
const els = {};
function el() { return { textContent: '', innerHTML: '', value: '', style: {}, classList: { add() {}, remove() {}, contains() { return false } }, addEventListener() {}, onclick: null } }
global.document = { getElementById: id => els[id] || (els[id] = el()), querySelectorAll: () => [], querySelector: () => el() };
global.navigator = {}; global.location = { protocol: 'file:' };
const store = {}; global.localStorage = { getItem: k => store[k] || null, setItem: (k, v) => store[k] = v, removeItem: k => delete store[k] };
global.confirm = () => false; global.Blob = function () {}; global.URL = { createObjectURL: () => '' };
global.window = global;
const vm = require('vm');
js = js.replace(/document\.querySelectorAll\('nav button'\)[\s\S]*?\}\);\n/, '');
js = js.replace(/renderToday\(\);\nif\('serviceWorker'[\s\S]*$/, '');
js = js.replace(/^\s*'use strict';/, '');
vm.runInThisContext(js);

let pass = 0, fail = 0;
function t(name, cond) { cond ? pass++ : (fail++, console.log('FAIL: ' + name)) }

t('weekOf start=1', weekOf('2026-09-01') === 1);
t('weekOf +7d=2', weekOf('2026-09-08') === 2);
t('weekOf Nov30=13', weekOf('2026-11-30') === 13);
t('phase wk1=LEARN', phaseOf(1) === 'LEARN');
t('phase wk7=DELOAD', phaseOf(7) === 'DELOAD');
t('phase wk12=DELOAD', phaseOf(12) === 'DELOAD');
t('phase wk13=FINAL', phaseOf(13) === 'FINAL');
t('phase pre=PREP', phaseOf(0) === 'PREP');
t('Sep1 Tue=lowerA', sessionFor('2026-09-01') === 'lowerA');
t('Sep6 Sun=off', sessionFor('2026-09-06') === 'off');
t('Sep7 Mon=upperA', sessionFor('2026-09-07') === 'upperA');
t('chips exist', PROTEIN_CHIPS.length === 9);

const msgs = coachFor('2026-09-03');
t('coach returns msgs', Array.isArray(msgs) && msgs.length >= 1);
t('learn phase msg', msgs.some(m => /LEARN/.test(m.t)));
const dm = coachFor('2026-10-13'); // week 7 -> deload
t('deload msg', dm.some(m => /DELOAD/.test(m.t)));

t('belly answer', /spot reduction/i.test(answer('why is my belly not going')));
t('abs answer', /12.14/.test(answer('when will i see abs')));
t('plateau answer', /weekly avg/i.test(answer('i plateaued')));
t('sore answer', /soreness/i.test(answer('legs sore')));
t('generic fallback', /plan already has a rule/i.test(answer('asdf qwerty')));

S.days['2026-09-01'] = { weight: 78 }; S.days['2026-09-02'] = { weight: 77.6 }; S.days['2026-09-03'] = { weight: 77.4 };
const wa = weeklyAvg('2026-09-03');
t('weeklyAvg computes', Math.abs(wa - 77.666) < 0.01);

S.days['2026-09-03'].protein = 170; S.days['2026-09-03'].supps = { creatine: true }; S.days['2026-09-03'].sleep = 8;
S.days['2026-09-02'].protein = 170; S.days['2026-09-02'].supps = { creatine: true };
t('dayHit works', dayHit('2026-09-03') === true);
t('streak counts', streak() >= 0);

const svg = chart('w', [78, 77.5, null, 77, 76.5], '#fff', '');
t('chart renders svg', svg.includes('<svg') && svg.includes('<path'));
t('chart sparse ok', chart('w', [null, 77, null], '#fff', '').includes('Not enough'));

S.days = {};
let c = S.profile.start; const end = '2026-09-20'; let w = 78;
while (c <= end) {
  const d = D(c); d.weight = +(w - Math.random() * 0.5).toFixed(1); w -= 0.105;
  d.protein = 150 + Math.round(Math.random() * 30); d.supps = { creatine: true };
  const sid = sessionFor(c);
  if (sid !== 'off' && sid !== 'cardio' && weekOf(c) >= 1) {
    SESSIONS[sid].ex.forEach((e, i) => { for (let s = 0; s < 3; s++) d.sets[i + '_' + s] = { kg: 12, reps: 9, done: true } });
  }
  c = addDays(c, 1);
}
t('demo generates days', Object.keys(S.days).length === 20);
try { renderToday(); renderPlan(); renderStats(); renderCoach(); renderSet(); t('renders ok', true) }
catch (e) { t('renders: ' + e.message, false) }
console.log(pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
