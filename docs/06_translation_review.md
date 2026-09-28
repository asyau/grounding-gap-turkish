# Native-speaker review of the hard translations (25 September 2026)

Reviewer: Asya Ünal, native Turkish speaker. Scope: the 29 stimuli flagged `hard` in
`data/stimuli_tr.csv`, meaning no clean one-to-one Turkish equivalent. Two further rows changed as a
knock-on, because a reviewed word was already assigned to another stimulus and no two English
stimuli may share a Turkish word.

The machine-readable log of every decision is `data/translation_review.json`. Each reviewed row in
the CSV has `reviewed = 2026-09-25 native speaker`, and a changed row keeps its previous
translation in `alternative`.

## Result

31 rows reviewed: 16 kept, 13 hard items changed, and 2 knock-on changes. The table still validates:
293 rows, all stimuli present, no duplicate Turkish targets.

### Changed

| English | Before | After | Origin after | Note |
| --- | --- | --- | --- | --- |
| compulsion | zorlantı | zorlama | hybrid | coercion sense rather than the clinical term |
| consideration | düşüncelilik | değerlendirme | native | reviewer's sense: "bir konuyu ciddiyetle ele alıp tartma", weighing a matter seriously |
| convention | teamül | uzlaşım | native | reviewer first chose gelenek, which is tradition's word |
| dismay | yılgınlık | dehşet | loan (Arabic) | took dehşet from horror |
| **horror** (knock-on) | dehşet | yoğun korku | native | "intense fear"; reviewer typed "yoğun kokru", read as a typo. Shares its root with fear (korku) |
| fun | keyif | eğlence | native | took eğlence from amusement |
| **amusement** (knock-on) | eğlence | eğlenme | native | same root as fun |
| home | yuva | ev | native | the concrete word for house |
| matter | mesele | madde | loan (Arabic) | the physical-matter sense |
| realization | farkındalık | farkına varma | hybrid | the moment of realizing |
| regard | itibar | saymak | native | a verb infinitive; same root as saygı (respect) |
| resolution | çözüm | önerge | native | a formal motion or resolution put to an assembly |
| scheme | entrika | tasarı | native | a plan or design; reviewer first chose plan, which is the stimulus plan's word |
| slapstick | kaba güldürü | şaklabanlık | hybrid (check) | buffoonery; the origin of şaklaban needs checking in Nişanyan |
| wonder | huşu | merak etmek | hybrid | "to wonder", a verb phrase; curiosity keeps merak |

### Kept after review

application (başvuru), argument (tartışma), aspect (yön), challenge (meydan okuma), dream (rüya),
frustration (hüsran), grace (incelik), memory (anı), model (model), occupation (meslek), order
(düzen), present (şimdiki zaman), romantic (romantiklik), self-dependence (kendine yeterlilik),
sensation (duyum), welfare (esenlik).

## Collisions resolved during the review

Six times the first choice was a word already assigned to another stimulus. Each was settled
with a follow-up question:

- convention chose *gelenek* (tradition) and settled on *uzlaşım*.
- dismay chose *dehşet* (horror); horror then chose *korku* (fear) and settled on *yoğun korku*.
- fun chose *eğlence* (amusement); amusement became *eğlenme*.
- scheme chose *plan* (plan) and settled on *tasarı*.
- self-dependence chose *bağımsızlık* (independence) and reverted to *kendine yeterlilik*.
- wonder chose *merak* (curiosity) and settled on *merak etmek*.

## What to keep in mind when reading the results

- **Flags were not changed.** The 29 items remain `hard`, so the notebook's robustness check on
  `ok` words only still excludes them. That is deliberate: the review settles which Turkish word
  to use, but it does not remove the underlying mismatch in meaning with the English stimulus.
- **Part of speech.** *saymak* and *merak etmek* are verbs, while almost every other stimulus is a
  noun. Property lists for verbs may differ in kind. If either stands out in the results, that is
  the first thing to check.
- **Sense choices that move away from the English norm's likely sense.** *madde* (physical matter),
  *ev* (house), and *önerge* (formal resolution) pick one sense of a polysemous English word. The
  human norms were collected in German, so the sense German participants had in mind is not known
  from the English list alone. Checking Harpaintner's German originals for these three would settle
  it.
- **Shared roots.** horror (*yoğun korku*) and fear (*korku*), fun (*eğlence*) and amusement
  (*eğlenme*), and regard (*saymak*) and respect (*saygı*) now share roots. Those pairs may produce
  similar property lists; that is a genuine feature of Turkish, but worth a sentence in any write-up.
- **Origins changed with the words.** After the review: 154 native (122 with a transparent concrete
  root), 25 hybrid, 114 loanwords. The within-Turkish contrast uses these updated labels. They still
  need checking against Nişanyan Sözlüğü.

## Not yet reviewed

The 61 items flagged `check`. They are defensible first-pass choices, and the notebook can run
without reviewing them. Reviewing them the same way (current word, alternatives, collision check)
would take about 16 rounds of four questions.
