# Research proposal: does the grounding gap hold in Turkish?

The one-page proposal written in August 2026 for a Bilkent individual research study. Kept as the
statement of the research question. Two things changed in the implementation:

- Step 2 proposed matching native and borrowed Turkish words on concreteness. The notebook instead
  uses each concept's own English profile as its baseline (a difference-in-differences), which
  controls for concept content without needing concreteness ratings for Turkish.
- The "no human norms" limitation is softer than stated below: the Harpaintner norms are from German
  speakers, so the English arm is itself a translation, and both arms can be scored against the
  same norms. See `04_parser_bug_and_turkish_design.md`.

---

**Asya Ünal** · Computer Engineering, Bilkent University · asya.unal@ug.bilkent.edu.tr

## Background

Chlapanis, Menis Mastromichalakis and Papadimitriou (arXiv 2605.08837, 2026) replicated
property-generation experiments from cognitive science on 21 large language models. Participants,
human or model, are given an abstract word such as *justice* and asked to list the properties that
come to mind. Responses are coded into four categories: sensorimotor, internal state and emotion,
social, and verbal association, and the per-word distributions are correlated against published
human norms.

Their result is a large and stable gap. No model exceeds Pearson r = 0.37 against humans, while the
human-to-human ceiling is about 0.97. Models systematically over-produce verbal associations and
under-produce internal-state properties. The gap does not shrink with model scale, and models
correlate far more strongly with each other than with people.

## The gap in the work

Every stimulus and every prompt in that study is in English. The authors interpret the result as a
property of text-based training in general. That interpretation has not been tested in a second
language, and English is an unusual place to test it: most English abstract vocabulary is Latinate
borrowing, so the words are etymologically opaque and carry no visible relationship to concrete
experience.

## Proposed contribution

Turkish offers a contrast that English cannot. It has a productive native morphology for deriving
abstract nouns from concrete or evaluative roots (*iyi* → *iyilik*, *güzel* → *güzellik*, *insan* →
*insanlık*), and it also carries a large stock of borrowed abstract vocabulary from Arabic, Persian
and French (*adalet*, *teori*). This permits a **within-language contrast that requires no human
norming data at all**:

> Do language models produce different grounding profiles for morphologically derived Turkish
> abstracts than for borrowed Turkish abstracts, when the concepts are matched for abstractness?

If the grounding a model recovers is driven by distributional co-occurrence alone, derivation should
make no difference. If a visible morphological link to a concrete root pulls the model toward
sensorimotor properties, that is evidence that surface form is doing work the paper attributes to
semantics, and it is a mechanism the original study could not see.

## Method

1. Translate the 293-word Harpaintner stimulus set and the generation and coding prompts into
   Turkish. Flag items where translation is not one-to-one rather than forcing them.
2. Split the Turkish stimuli into natively derived and borrowed abstracts, matched on the
   concreteness ratings used in the original work.
3. Run the published pipeline on two or three models. The authors' code is public at
   github.com/odychlapanis/grounding-gap, and their evaluation scripts reproduce the paper's
   leaderboards with no API key, so the reproduction step costs nothing.
4. Compare per-category distributions three ways: Turkish against English for the same model,
   derived against borrowed within Turkish, and both against the published human norms.

## Deliverable

A written report with the comparison figures, the code, and an honest limitations section. If the
within-language contrast holds, a workshop paper is a realistic target.

## The limitation, and where supervision would matter most

No Turkish human property-generation norms exist. Without them, the Turkish-versus-English
comparison measures how the *model* behaves across languages, not how the *gap* differs. The
within-language contrast in step 2 avoids this, which is why it is the primary question rather than
the secondary one.

**Collecting even a small Turkish norming set would remove the limitation entirely**, and that is
the part that cannot be done alone. It needs participants, an ethics review, and someone who has
designed a human study before. It is the natural second half of the project.
