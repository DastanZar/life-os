# Competitive Analysis: Cronometer, MyFitnessPal, MacroFactor, Hevy/Strong
*What the best-in-class apps teach us for BODY OS · researched 2026-09-03*
*Sources: cronometer.com/features + support docs + blog ("10 Ways To Log Food Faster"), calorie-trackers.com 2026 head-to-head (tested Mar–Aug 2026), caloriescanai 2026 comparison, r/cronometer redesign thread + ads thread, r/MyFitnessPal paywall/exodus threads (2022–2026), macrofactor.com "Algorithms & Core Philosophy" + "Adherence Neutral" posts, Hevy-vs-Strong 2026 comparisons (85k–108k ratings, 4.86–4.92★).*

---

## 1. The market in one paragraph

Two philosophies split the category. **Cronometer** = verified data + depth (84 nutrients, USDA/NCCDB sources, ±3.5% calorie accuracy) for people who care about what's in the food. **MyFitnessPal** = breadth + speed (14M mostly user-submitted foods, ±6.8% accuracy, 50+ device integrations) for people who just want to log fast. MFP is now actively bleeding users ("outdated, ad-choked, paywalled to death" — Reddit consensus after they paywalled the barcode scanner in 2022 and kept moving free features behind premium). Cronometer won the accuracy war but is *losing trust right now* by bombard-ing free users with ads (Nov 2025 thread: users actively hunting alternatives). Meanwhile **MacroFactor** carved a third lane — behavioral-science design — and **Hevy/Strong** proved that in workout logging, *speed of a single set-log is the entire product*.

## 2. Design lessons (ranked by how much they'd move BODY OS)

### L1. The diary IS the home screen — never bury it
Top complaint on Cronometer's 2022 redesign: *"99% I'm opening Cronometer, it's to add food"* — and the new dashboard pushed logging behind a tap. **Lesson:** our Today tab is right, but logging must be the FIRST thing under the thumb. Every screen we design should answer "how fast can he log one thing?"

### L2. Logging speed is retention (Hevy/Strong's whole moat)
Strong's reputation = "the fastest way to log a lift." Hevy 4.92★ on the same. Their tricks: pre-loaded session from template, one-tap set completion, big tap targets, rest timer auto-starting, last weights prefilled. **Lesson:** our set rows should prefill kg/reps from last week's same exercise, and the ✓ button should auto-start a rest countdown.

### L3. Adherence-neutral design (MacroFactor's philosophy — the big one)
MacroFactor deliberately ships **no red warning bars, no shame notifications, no streak-breaking guilt**: "one missed day does not break your progress." Their reasoning: shame → abandonment; the algorithm solves for energy expenditure, so adherence is *data, not morality*. **Lesson:** our protein ring turns RED at <70% and the coach says "decide before 9pm, not after" — that's guilt-framing. Reframe: ring stays neutral, shows "remaining" not "failing"; coach tone shifts from nagging to informing. (Keep the streak — it's positive-only framing, which is allowed.)

### L4. Two inputs, not ten (MacroFactor's onboarding promise)
*"All you have to do is track your food and log your weight. That's it."* The app derives everything else. **Lesson:** our Daily Five is already close, but we should make 3 of the 5 (steps, water, even kcal) *optional auto/estimate* and treat protein + weight + session-logged as the sacred three.

### L5. Progressive disclosure of depth (Cronometer's flaw)
Review consensus: Cronometer's nutrient density "overwhelms new users; most adapt after a week." **Lesson:** BODY OS v1 shows exactly the right depth for a beginner. Micronutrients (B12, vitamin D, iron — relevant for vegetarians!) go behind a "Nutrition detail" toggle, added ~week 4 when the habit exists.

### L6. Favorites, quick-add, recipes (Cronometer's actual daily-use features)
From their support docs + "log food faster" blog: star-favorite foods → Favorites tab; swipe-right on saved food = instant log; **custom recipes** (save "my oats bowl" = 5 ingredients, one tap); diary groups (Breakfast/Lunch…) with per-meal nutrient breakdown; per-group quick-add menus. **Lesson:** this is our biggest functional gap — see F1 below.

### L7. Don't monetize friction (both incumbents' self-inflicted wounds)
MFP paywalled barcode → mass exodus. Cronometer ad-bombarded → churn threads. **Lesson:** BODY OS is local + free forever; make that *visible* ("no ads, no premium, your data on your phone") — it's a genuine differentiator against both.

### L8. Trend-smoothed charts + derived metrics (MacroFactor's charts)
Their energy-expenditure chart and smoothed weight trend are called out in reviews as "genuinely useful for decisions." **Lesson:** our weight chart should add a moving-average trend line and an **estimated TDEE line** (intake − weekly-loss-rate × 7700×7) — turns the app from logger into calculator.

## 3. Functional gaps found → v2 feature list

| # | Feature | Borrowed from | Effort |
|---|---|---|---|
| F1 | **Food diary with real entries** — each logged food = kcal + P/C/F, listed under Breakfast/Lunch/Dinner/Snacks, tap-to-delete. Replaces the +6g-chips-only model | Cronometer diary groups | M |
| F2 | **Favorites + recents** — star a food once, one-tap forever; "you logged this yesterday" suggestions | Cronometer favorites/swipe-add | S |
| F3 | **Custom recipes** — "My dal bowl" = dal+rice+curd saved as one item with auto-summed macros | Cronometer recipes | M |
| F4 | **Prefill sets from last week + rest timer** — session screen shows last weights; ✓ starts 90s countdown | Hevy/Strong | S |
| F5 | **Adherence-neutral reskin** — neutral ring ("remaining"), coach tone pass (inform, don't scold) | MacroFactor | S |
| F6 | **Auto-adjusting targets** — weekly: est. TDEE from smoothed trend → suggest next week's kcal (his Sunday review becomes a one-tap approve) | MacroFactor algorithm | M |
| F7 | **Trend line + TDEE chart** on Stats | MacroFactor | S |
| F8 | **Workouts inline in diary timeline** — day view shows food AND session AND biometrics together | Cronometer | S |
| F9 | **Micronutrient nudge for vegetarians** (B12/iron/D/zinc from food entries, behind a toggle, unlocked week 4) | Cronometer's moat, adapted | M |
| F10 | **"No ads, no paywall, local data" badge** in About | anti-MFP positioning | XS |

**Deliberately NOT copying:** barcode scanning (needs camera + 14M-food DB — native-app territory), 50+ integrations (PWA can't; Google Fit import is a maybe later), photo-logging AI (Cronometer's new toy; needs server + cost), social feeds (Hevy's community — irrelevant for a personal Life OS chart).

## 4. What we already do better than all four

- **A coach with a plan, not a database** — none of them know *why* he's training; ours encodes the 13-week protocol, deloads, and the science citations
- **Waist-first framing** — all four are scale-centric; we already tell him the tape is truth
- **LLM memory of his actual conversations** (the glm/qwen coach) — MacroFactor's "coach" is a static algorithm; ours can answer "my lower back is tight, train Saturday?" with context
- **Zero-friction start** — no account, no onboarding quiz, no paywall wall

## 5. Recommended build order

**v2.0 (this week):** F4 prefill+rest timer → F5 adherence-neutral pass → F7 trend/TDEE chart → F10 badge *(all small, high daily-use impact)*
**v2.1 (next):** F1 food diary + F2 favorites/recents *(the big one — turns protein-tracking into nutrition-tracking)*
**v2.2:** F3 recipes → F6 auto-adjust → F8 inline workouts
**v3 (week 4+):** F9 micronutrients for vegetarians

---
*Raw sources archived in /tmp/appresearch/ (cronometer features page, both 2026 comparisons). Reddit fetched via search-snippet mining (direct API blocked).*
