// Student-facing PDF (supervisor feedback, topic brief): Quarto Typst template partial.
// Keeps Quarto's `article()` signature so the stock `typst-show.typ` calls it unchanged.
// Per-render values (kind, labels, student, topic, draft stamp) come from the `masthead`
// metadata that the kind's layout filter assigns; colours and the font family are the only
// house-style knobs. A masthead row whose value is absent is left out.

#let fb-accent = rgb("#1f4e79")
#let fb-muted = rgb("#5b6470")
#let fb-rule = rgb("#d5dbe3")
#let fb-zebra = rgb("#f4f6f9")
#let fb-font = ("Noto Sans",)

#let fb-meta = (
  kind: [$masthead.kind$],
  student-label: [$masthead.labels.student$],
  topic-label: [$masthead.labels.topic$],
  date-label: [$masthead.labels.date$],
  student: $if(masthead.student)$[$masthead.student$]$else$none$endif$,
  topic: $if(masthead.topic)$[$masthead.topic$]$else$none$endif$,
  draft: $if(masthead.draft)$[$masthead.draft$]$else$none$endif$,
)

// Quarto's callout is unbreakable and boxed twice; a feedback item can run half a page, so
// this one breaks across pages and is a tinted block with an accent bar on the left.
// Quarto's callout palette is loud (important = alarm red); map each kind to a calmer tone.
#let fb-callout-tone(c) = {
  if c == rgb("#cc1914") { rgb("#b4462a") }       // important: P1
  else if c == rgb("#00a047") { rgb("#2f7d5b") }  // tip: P2, progress, what works
  else if c == rgb("#0758e5") { rgb("#4a6a8c") }  // note: review scope
  else if c == rgb("#eb9113") { rgb("#b7791f") }  // warning
  else { c }
}

#let callout(body: [], title: none, background_color: none, icon: none, icon_color: black, body_background_color: none) = {
  let tone = fb-callout-tone(icon_color)
  block(
    breakable: true,
    width: 100%,
    fill: tone.lighten(92%),
    stroke: (left: 3pt + tone),
    inset: (left: 11pt, right: 10pt, y: 9pt),
    radius: (right: 3pt),
    above: 1.1em,
    below: 1.1em,
  )[
    #if title != none and title != [] {
      block(below: 0.6em, sticky: true, text(weight: "bold", fill: tone.darken(25%), size: 1.02em, title))
    }
    #body
  ]
}

#let article(
  title: none,
  subtitle: none,
  authors: none,
  keywords: (),
  date: none,
  abstract-title: none,
  abstract: none,
  thanks: none,
  cols: 1,
  lang: "cs",
  region: none,
  font: none,
  fontsize: 10.5pt,
  title-size: 1.5em,
  subtitle-size: 1.25em,
  heading-family: none,
  heading-weight: "bold",
  heading-style: "normal",
  heading-color: black,
  heading-line-height: 0.65em,
  mathfont: none,
  codefont: none,
  linestretch: 1,
  sectionnumbering: none,
  linkcolor: none,
  citecolor: none,
  filecolor: none,
  toc: false,
  toc_title: none,
  toc_depth: none,
  toc_indent: 1.5em,
  doc,
) = {
  set document(title: title, keywords: keywords)
  set text(lang: lang, size: fontsize, font: fb-font)
  set par(justify: false, leading: 0.68em, spacing: 0.95em)

  set page(
    paper: "a4",
    margin: (x: 22mm, top: 24mm, bottom: 22mm),
    // In the foreground, so no card fill can hide it on a preview.
    foreground: if fb-meta.draft != none {
      place(center + horizon, rotate(-35deg, text(size: 72pt, weight: "bold", fill: luma(120).transparentize(82%), fb-meta.draft)))
    },
    header: context {
      if counter(page).get().first() > 1 {
        set text(size: 8.5pt, fill: fb-muted)
        grid(columns: (1fr, auto), title, [#fb-meta.student])
        v(-2pt)
        line(length: 100%, stroke: 0.5pt + fb-rule)
      }
    },
    footer: context {
      set text(size: 8.5pt, fill: fb-muted)
      align(right)[#counter(page).display("1") / #counter(page).final().first()]
    },
  )

  show heading: set text(fill: fb-accent)
  show heading.where(level: 2): it => block(above: 1.6em, below: 0.8em, sticky: true)[
    #set text(size: 1.25em, weight: "bold")
    #it.body
    #v(-0.45em)
    #line(length: 100%, stroke: 0.8pt + fb-rule)
  ]
  show heading.where(level: 3): set text(size: 1.05em, weight: "bold")

  show link: set text(fill: fb-accent)
  set list(indent: 0.4em, body-indent: 0.5em, spacing: 0.75em)
  set enum(indent: 0.4em, body-indent: 0.5em, spacing: 0.85em)

  set table(
    inset: (x: 7pt, y: 6pt),
    stroke: (x, y) => (bottom: 0.5pt + fb-rule),
    fill: (x, y) => if y == 0 { fb-accent } else if calc.even(y) { fb-zebra } else { none },
  )
  show table.cell.where(y: 0): set text(fill: white, weight: "bold")
  show table: set text(size: 0.92em)

  // Title block: what this is, for whom, about what, when.
  block(width: 100%, below: 1.4em)[
    #text(size: 9pt, fill: fb-muted, weight: "bold", tracking: 0.08em, upper(fb-meta.kind))
    #v(0.2em)
    #text(size: 20pt, weight: "bold", fill: fb-accent, title)
    #v(0.6em)
    #set text(size: 9.5pt)
    #let rows = ()
    #if fb-meta.student != none { rows += (text(fill: fb-muted, fb-meta.student-label), fb-meta.student) }
    #if fb-meta.topic != none { rows += (text(fill: fb-muted, fb-meta.topic-label), fb-meta.topic) }
    #if date != none { rows += (text(fill: fb-muted, fb-meta.date-label), date) }
    #grid(columns: (auto, 1fr), column-gutter: 10pt, row-gutter: 5pt, ..rows)
    #v(0.4em)
    #line(length: 100%, stroke: 1.2pt + fb-accent)
  ]

  doc
}
