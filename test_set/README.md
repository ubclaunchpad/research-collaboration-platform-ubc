# Match test set

30 student and professor pairs used to score every version of search against the same yardstick. The professors are the 10 researchers in `sample_data/` (RES-25), and everything we know about them comes from OpenAlex only.

## What a good match is

A good match is a professor this student would reasonably email. The professor's published work overlaps with what the student wants to work on, and the student's skills could help with it. Judge on research topic first and skills second. Being at UBC, being well known, or sharing a word that means something different does not count.

## The score

Top-3 hit rate: for each student, search ranks all 10 professors. The student is a hit if at least one professor rated good for them is in the top 3. Students with no good professor are left out.

Each search version is also measured on:

- median seconds per search
- AI calls per search

Proposed first-pilot target, still to be agreed with the leads:

| Measure | Target |
|---|---|
| Top-3 hit rate | at least 80% |
| Median time per search | 3 seconds or less |
| AI calls per search | 1 or fewer |

Before trusting a score, also score a random ordering. With only 10 professors, top 3 is easy to hit by luck.

## pairs.csv

One row per pair. 10 made-up students, each paired with 3 professors: one clear fit, one clear misfit and one tricky case. There are 20 obvious pairs and 10 tricky ones.

| Column | Meaning |
|---|---|
| `pair_id` | Id of the pair, `P01` to `P30` |
| `student_id` | Made-up student, `S01` to `S10` |
| `student_major` | Major of the student |
| `student_interests` | What the student wants to work on |
| `student_skills` | Skills the student has |
| `researcher_id` | Row id in `sample_data/researchers.csv` |
| `researcher_name` | Professor name |
| `openalex_id` | Author id in OpenAlex |
| `researcher_topics` | Top 5 OpenAlex topics of the professor, separated by `; ` |
| `researcher_keywords` | Top 5 OpenAlex keywords of the professor, separated by `; ` |
| `case` | `obvious` or `tricky` |
| `why_tricky` | Why the pair is hard, empty for obvious pairs |
| `rater_1`, `rater_2` | `good` or `not good`, from two people who rate on their own |
| `final_rating` | The agreed rating |
| `settled_note` | How a disagreement was settled |

## Rating

Two team members rate every pair first, without seeing each other's answer. Where they differ they talk it through and write the outcome in `settled_note`. Volunteers re-rate later (RES-34, RES-74).

The rating columns are empty until the raters fill them in.

## Known rough edges

- Only 10 professors, so this checks ranking at a small scale.
- Topics and keywords for Kevin Leyton-Brown and Laks Lakshmanan come from their main OpenAlex record. OpenAlex splits each of them into two records.
- `researcher_id` and the professor list come from `sample_data/`, which arrives with the RES-25 PR.
