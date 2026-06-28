# Cover Letter Templates and Tailoring Guide

## Template: Custom cover.cls (XeLaTeX)

Cover letters use a custom LaTeX document class (`cover.cls`) with Lato/Raleway fonts.

**Output file:** `cover_letters/cover_<company>_<role>.tex`
**Compile with:** XeLaTeX (cover.cls requires fontspec)
**Font directory:** `cover_letters/OpenFonts/fonts/`

### Compile command

```bash
cd cover_letters && xelatex -interaction=nonstopmode cover_<company>_<role>.tex
```

Expected output: `Output written on cover_<company>_<role>.pdf (1 page, ...)`. Any page count other than 1 is a failure that must be fixed before presenting to the user.

## Compile-and-Inspect Loop (MANDATORY)

After writing the cover letter and before presenting to the user, always compile and visually inspect the PDF. Iterate until the layout is clean:

1. Run `xelatex -interaction=nonstopmode cover_<company>_<role>.tex`
2. Confirm page count is exactly 1 and compile succeeded
3. Read the PDF via the Read tool and visually check: signature fits at the bottom, no text cut off, bullet font matches body

### Known template pitfall: itemize inside `\lettercontent{}`

The `\lettercontent{}` macro appends `\\` to its argument. This breaks when the argument ends in `\end{itemize}` because `\\` has no line to break after the environment closes, producing `! LaTeX Error: There's no line here to end.` and no PDF output.

**Wrong (breaks compile):**
```latex
\lettercontent{Here is how my experience maps:
\begin{itemize}
    \item ...
\end{itemize}}
```

**Correct — close `\lettercontent{}` before the list and wrap the list in the matching Raleway-Medium font so typography stays consistent:**
```latex
\lettercontent{Here is how my experience maps:}

{\raggedright\fontspec[Path = OpenFonts/fonts/raleway/]{Raleway-Medium}\fontsize{11pt}{13pt}\selectfont
\begin{itemize}
    \item ...
\end{itemize}\par}
\vspace{6pt}

\lettercontent{[next paragraph]}
```

The font wrapper is mandatory — if you just move `\begin{itemize}` outside `\lettercontent{}` without the `\fontspec` block, bullets render in the default body font (Lato) and visually mismatch the rest of the letter.

## Document Structure

```latex
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Cover Letter - [Company], [Role]
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\documentclass[]{cover}
\usepackage{fancyhdr}

\pagestyle{fancy}
\fancyhf{}

\rfoot{Page \thepage \hspace{0pt}}
\thispagestyle{empty}
\renewcommand{\headrulewidth}{0pt}
\begin{document}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%     TITLE NAME
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\namesection{}{\Huge{Siddhant Gupta}}{  \href{mailto:siddhantbenz@gmail.com}{siddhantbenz@gmail.com} | +47 92206297 |  \urlstyle{same}\href{https://www.linkedin.com/in/siddhantgupta1996}{LinkedIn}
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%     MAIN COVER LETTER CONTENT
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\currentdate{\today}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Cover Letter - [Company], [Role]
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\documentclass[]{cover}
\usepackage{fancyhdr}

\pagestyle{fancy}
\fancyhf{}

\rfoot{Page \thepage \hspace{0pt}}
\thispagestyle{empty}
\renewcommand{\headrulewidth}{0pt}
\begin{document}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%     TITLE NAME
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\namesection{}{\Huge{Siddhant Gupta}}{  \href{mailto:siddhantbenz@gmail.com}{siddhantbenz@gmail.com} | +47 92206297 |  \urlstyle{same}\href{https://www.linkedin.com/in/siddhantgupta1996}{LinkedIn}
}

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%     MAIN COVER LETTER CONTENT
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

\currentdate{\today}
\lettercontent{Dear [Name/Team],}

\lettercontent{[Opening paragraph - role, connection to background, 2-3 sentences]}

\lettercontent{[Body paragraph - most relevant experience, then bullet list:]}

{\raggedright\fontspec[Path = OpenFonts/fonts/raleway/]{Raleway-Medium}\fontsize{11pt}{13pt}\selectfont
\begin{itemize}
    \item [Concrete achievement/skill 1]
    \item [Concrete achievement/skill 2]
    \item [Concrete achievement/skill 3]
\end{itemize}\par}
\vspace{6pt}

\lettercontent{[Connection to company - why this role, why this company specifically]}

\lettercontent{[Personal fit paragraph - behavioral strengths, team contribution, 2-3 sentences]}

\lettercontent{I look forward to hearing from you.}

\begin{flushright}
\closing{Kind regards,\\}

\signature{Siddhant Gupta}
\end{flushright}
\end{document}
```

## Key Commands Reference

| Command | Purpose |
|---------|---------|
| `\namesection{}{Name}{contact info}` | Header with name and contact |
| `\currentdate{date}` | Date field (use `\today` or explicit date) |
| `\lettercontent{text}` | Body paragraph (adds spacing after) |
| `\closing{text}` | Closing line |
| `\signature{name}` | Printed name below signature |

## Tailoring Guidelines

### Salutation
- If you know the hiring manager's name: "Dear [First Last],"
- Generic: "Dear [Company]," (avoid "To whom it may concern")

### Length - Hard 1-Page Limit
- Target: 1 page including signature block
- Maximum: **never exceed 1 page**
- **Word budget: 250-300 words** of body text (not counting LaTeX markup). This is the safe maximum. 350 words will overflow.
- **Always count**: opening paragraph + bullet list paragraph + closing paragraph = 3 blocks. Add a 4th only if the others are short.
- When adding company-specific content, trim other content to compensate rather than adding net length

### Line Spacing
- Add `\usepackage{setspace}` and `\setstretch{1.0}` if the letter is long and needs to fit on one page
- Use `\vspace{.5cm}` between major sections for readability (only if space permits)

### Bullet Lists
- Place `\begin{itemize}...\end{itemize}` **outside** a `\lettercontent{}` block (see "Known template pitfall" above), wrapped in the matching Raleway-Medium `\fontspec` so the bullet font matches the body
- 3-5 bullets is ideal
- Start each bullet with bold label or action verb
- Use `\textbf{Label:}` for category-style bullets

### LaTeX Special Characters
- Underscore: `\_`
- Ampersand: `\&`

### Non-English Cover Letters
- Same template structure, just write content in the posting's language
- Adjust date format to local convention
- Adjust closing to local convention (e.g. "Med vennlig hilsen," for Norwegian)

## Hard Rules

These are not suggestions. These rules must be enforced before a cover letter is considered final.

### Rule 1: At least one quantified outcome
The cover letter body must contain at least one quantified achievement from the CV. Zero-metrics letters are rejected. The candidate's CV has numbers (25-30% reduction, 5+ municipalities, 70+ power plants, 3 core products). Pick one and weave it into the body paragraph.

Example:
> **Weak:** "I have experience building data pipelines for sustainability reporting."
> **Better:** "I engineered ETL pipelines that automated GHG accounting across 5+ municipalities, reducing manual mapping effort."

### Rule 2: At least 2 specific, independently-verified company facts
Every company-specific claim in the cover letter must refer to a concrete, verifiable fact about the company. Generic mission statements ("industry leadership in sustainable X") are not enough. Acceptable:
- A specific project they announced (e.g., "Hydro's post-consumer scrap sorting facility at Clermont-Ferrand")
- A strategic initiative (e.g., "Statkraft's 2 GW onshore wind portfolio under development")
- A technology/platform (e.g., "your data platform using Databricks and Azure")

Before including any company fact, verify it via WebSearch/WebFetch. Do not trust reviewer agent research at face value.

### Rule 3: Template-consistency check
The cover letter MUST use `\documentclass[]{cover}`. Do NOT use `article`, `scrartcl`, or any other document class. The `cover.cls` class provides the branded header, correct fonts (Lato/Raleway), and proper signature block. Using any other class produces a visually inconsistent document.

### Rule 4: CV repetition test
After writing the cover letter, run this test:

> **"Can any sentence in the cover letter be lifted from the CV and still make sense? If yes, rewrite that sentence."**

The cover letter is not a CV summary. Its job is forward-looking: problems you'll solve for the employer, not what you've already done. Every paragraph should describe work the employer needs done, with past experience used only as brief evidence that you can do it.

### Rule 5: Behavioral tone match
The cover letter's voice must match the candidate's behavioral profile from `02-behavioral-profile.md`:
- **Analytical Problem-Solver** profile → lead with methodical approach, structured thinking
- **High Collaboration** → include team/ stakeholder language, frame achievements with "we" or cross-functional context
- Do NOT give a "Collaborator" profile a solo-hero, combative tone
- Do NOT give an "Analytical Problem-Solver" profile purely emotional appeals

## Checklist Before Finalizing
- [ ] No em-dashes (use commas or periods instead)
- [ ] No cliches or empty filler
- [ ] Every claim backed by specific example
- [ ] Forward-looking framing: focuses on tasks you'll solve, not just past duties
- [ ] Motivation section references this specific company's mission/values
- [ ] Company name and role are correct throughout
- [ ] Date is current
- [ ] Fits on one page
- [ ] Language matches the job posting language
- [ ] Salutation is appropriate (named person if possible)
- [ ] Headline is engaging and specific, not generic
- [ ] Uses \documentclass[]{cover} (not article or other class) — **MANDATORY**
- [ ] Contains at least 1 quantified outcome — **MANDATORY**
- [ ] Contains at least 2 specific, verified company facts — **MANDATORY**
- [ ] Passes the CV repetition test (no sentence that could be lifted from the CV) — **MANDATORY**
- [ ] Tone matches behavioral profile from 02-behavioral-profile.md — **MANDATORY**

## Submission Guidelines (Best Practice)
- Submit only the documents the employer requests
- Export as PDF to preserve formatting
- Name files clearly: "[Your Name] CV" and "[Your Name] Cover Letter"
- Follow all employer instructions regarding anonymity or specific materials
