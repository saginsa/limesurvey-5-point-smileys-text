# Changelog

## 2.1.0 — 2026-11-22

Back to the look of 1.0: the faces are characters again, sized with `font-size` and coloured with `color`.

- The faces come from a small embedded font (five glyphs of Font Awesome Free, outline and filled, about 1.3 KB
  each, renamed "Smileys Faces" as its license requires) on the same Unicode characters as in 1.0:
  U+1F620, U+2639, U+1F610, U+263A, U+1F600. The selected face is the filled glyph in its colour.
- Default size `x-large` and the text colour of the survey theme, as in 1.0; no hover or zoom effects.
- No focus outline after a click (the survey theme's outline is reset inside the question);
  keyboard focus shows a thin line under the face.
- `LICENSE-fonts.txt` (SIL OFL 1.1 and attribution) is part of the zip.

## 2.0.0 — 2026-11-22

First public release.

- Own SVG icons in the stylesheet instead of the embedded icon font of another survey product, which may not
  be redistributed. No web fonts or images are loaded; sizes, colours and icons are CSS variables.
- Styles are scoped to the question: 1.0 also removed the circles of the radio buttons of every other question
  on the same page.
- "No answer" of optional questions is shown with its text (in 1.0 it was a bare dot).
- The faces no longer overlap in the Vanilla and Fruity TwentyThree survey themes.
- Accessibility: the label text "1"…"5" is kept for screen readers, keyboard focus is visible,
  Windows high contrast mode and reduced motion are supported, a larger click target.
- Templates follow the core `5pointchoice` templates of LimeSurvey 6/7 (list markup, quoted attributes).
- Preview image for the question theme list.
- Tests: static checks and Docker integration tests on LimeSurvey 6.17, 7.5 and 7.10; GitHub Actions.

## 1.0 — 2022-12-11

Internal version: the faces of "5 Point Emojis" by Tony Partner as glyphs of an embedded icon font.
