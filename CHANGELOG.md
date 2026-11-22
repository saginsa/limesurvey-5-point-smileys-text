# Changelog

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
