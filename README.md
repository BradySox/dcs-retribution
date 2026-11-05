# RetLab campaigns: Germany Cold War and Afghanistan

Five campaigns built in RetLab (a DCS Retribution fork). Copy `resources/` over a Retribution
install; each campaign needs its `.yaml`, its `.miz` and the faction files listed below.

| Campaign | Map | Start | Player faction | Enemy faction | Mods |
|---|---|---|---|---|---|
| Germany - Fulda Gap 1985 | GermanyCW | 1985-09-10 | USAF 1985 | Warsaw Pact Central Front 1985 | stock only |
| Germany - Northern Shield 1988 (work in progress) | GermanyCW | 1988-07-24 | Blufor Late Cold War (80s) | Russia 1980 (Red Tide) | stock only |
| Germany - Red Tide | GermanyCW | 1988-07-13 | NATO Central Front 1985 | Russia 1980 (Red Tide) | stock only |
| Germany - Baltic Fury | GermanyCW | 2027-07-17 | NATO Baltic 2027 | Redfor (Russia) 2020 | Super Hornet, F-22, CurrentHill USA/UK/Sweden/Russia packs, High Digit SAMs |
| Afghanistan - Red Bear 1985 | Afghanistan | 1985-01-15 | USAF 1985 | USSR 40th Army 1985 | stock only |

Faction files shipped here (RetLab-only): `russia_1980_red_tide`, `ussr_40th_army_1985`,
`warsaw_pact_central_front_1985`, `nato_baltic_2027`, `nato_central_front_1985`, `usaf_1985`.
`Redfor (Russia) 2020` and `Blufor Late Cold War (80s)` are upstream factions.

## Notes for porting

- Yaml keys upstream does not read: `victory` (custom win/lose conditions) and
  `neutral_border_postures` (Fulda Gap only; neutral-country border defense). Upstream ignores
  them; the campaigns still load.
- Supply lines are M-113 route groups and sea lanes HandyWind groups in the `.miz`, as upstream draws them.
- Fulda Gap 1985 has rail lines drawn as `Train` groups; without RetLab's train support they are ignored.
- Groups named `FIXED ...` generate unit-for-unit as drawn in RetLab; upstream treats them as ordinary groups.
- Northern Shield 1988 is not final; its laydown is still being edited.
