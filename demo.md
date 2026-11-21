# MockMate demo script

Exact inputs to reproduce the full demo. Model wording will differ between runs and providers; what must match is the **shape** of each output (marked below). Run it with a real key, or set `MODEL_PROVIDER=fake` for a fully deterministic offline run.

Start from a clean state:

```bash
rm -f workspace/weak-topics.md workspace/sessions/*.md workspace/.checkpoints.sqlite*   # Windows: del those files
```

## 1. First interview (`--thread demo1`)

```bash
uv run python main.py --thread demo1
```

| Prompt | Type |
|---|---|
| What role are you preparing for? | `ML engineer, campus placement` |
| Which round | `ML fundamentals` |
| Difficulty | `medium` |
| Question 1 answer (deliberately bad) | `idk` |
| Question 2 answer | `It adds a penalty on squared weights to the loss so the weights shrink, which lowers variance because the model gets smoother.` |
| Remaining answers | `/quit` after question 3 (see step 2) |

Expected shape:

```text
MockMate Starting a ML fundamentals interview for ML engineer, campus placement (medium), 5 questions.
MockMate Question 1 of 5  [<topic>]
         <exactly one question>
You      idk
MockMate Score  <0-2>/10                     <- bad answer must not score high
         Landed <two strengths>
         Missed <two gaps>
         Hint   <one hint>
         Saved workspace/sessions/<date>_demo1.md
MockMate Question 2 of 5  [<topic>]
```

Checks: only one question is shown at a time; `workspace/sessions/<date>_demo1.md` exists and contains `role:` and `round:` lines.

## 2. Quit and resume (requirement 6)

At question 3 type `/quit`. Then:

```bash
uv run python main.py --thread demo1
```

Expected: `Resuming thread 'demo1': ML fundamentals for ML engineer, campus placement (medium), question 3 of 5.` and the same question 3 again. A different id (`--thread demo2`) starts clean with the setup questions.

Finish the interview (answer the rest). Expected at the end:

```text
MockMate Created workspace/weak-topics.md.
=== MockMate report (from workspace/sessions) ===
Sessions: 1   Answers: 5   Average: <n>/10
...
Weakest topics:
  - <topic> (ML fundamentals): avg <n> over <k> attempt(s)
```

## 3. Second run uses the weak topics (requirement 7)

```bash
uv run python main.py --thread demo3
```

Type `ML engineer`, `ML fundamentals`, `medium`. Expected first line after setup:

```text
MockMate Loaded weak topics from workspace/weak-topics.md: <topic from demo1>, .... Starting there.
```

## 4. Approval gate (requirement 8)

Finish `demo3` by answering `idk` to every question. At the end, expected:

```text
[approval needed] MockMate wants to overwrite workspace/weak-topics.md
<diff>
[a]pprove / [e]dit (drop topics) / [r]eject >
```

Type `r`. Expected: `Rejected. workspace/weak-topics.md was left unchanged.` Confirm with `git diff --no-index` or by checking the file's modified time: it did not change.

## 5. Workspace fence (requirement 9)

```bash
uv run python main.py --delete ../../outside.txt
uv run pytest tests/test_workspace.py -q
```

Expected: `Refused: '../../outside.txt' ... is outside the workspace.` with no prompt, and all fence tests pass (`../secrets.txt` and `/tmp/outside.txt` are refused).

## 6. Delete approval

```bash
uv run python main.py --delete <date>_demo1.md
```

Answer `n`: `Rejected. File left untouched.` Answer `y`: the file is deleted.

## 7. Reproducible report

```bash
uv run python main.py --report
```

The report is rebuilt only from `workspace/sessions/`, so running it twice prints identical output.
