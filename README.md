# Bayesian Workflow Claude Code Plugin

This plugin provides a workflow that runs in Claude Code.
The workflow is built to be run end to end, but we also provide a set of skills.

Currently the plugin is configured to use Stan and ArviZ.

When run end to end:

```mermaid
flowchart TD
  subgraph E ["Explore"]
    P["profile data"] --> A["EDA analysts, in parallel"] --> S1["synthesize one report"]
  end
  S1 --> G1{{"user confirms the goal"}}
  subgraph D ["Design"]
    F["frame the analysis"] --> DQ["one designer per structural question"] --> S2["dedup into an experiment plan"]
  end
  G1 --> F
  S2 --> G2{{"user approves the plan"}}
  subgraph V ["Develop"]
    Q["experiment queue"] --> ST["stages: prior predictive check,<br/>fake-data recovery, fit,<br/>posterior predictive check"]
    ST -->|"a stage fails, refine budget left"| FIX["refiner: FIX variant"] --> ST
    ST -->|"a stage fails, budget spent"| SK["skip experiment"]
    ST -->|"all pass"| C["critic: VIABLE / CONCERNS / BROKEN"]
    C --> STR["strategist: close questions, propose<br/>EXPLORE variants and new questions, or stop"]
    SK --> STR
    STR -->|"proposals that pass the guards<br/>(plateau, explore budget, question slots, experiment cap)"| NW["refiner: EXPLORE variants<br/>designer: new questions"] --> Q
    STR -->|"stop, nothing proposed, or round cap"| SEL["selector: ranking + coverage audit"]
    SEL -->|"coverage gaps, once"| GP["design and run gap experiments"] --> SEL
  end
  G2 --> Q
  subgraph R ["Report"]
    O["outline"] --> FS["fact sheet + figures"] --> W["section writers, in parallel"] --> AS["assemble"] --> CR["critic"]
    CR -->|"REVISE, revisions left"| RV["assembler revises"] --> CR
    CR -->|"SHIP, or revisions spent"| OUT["final report"]
  end
  SEL -->|"selected model"| O
```

## Install

```
/plugin marketplace add sunxd3/bayesian-statistician-plugin
/plugin install bayesian-workflow@sunxd3-plugins
```

Needs [`uv`](https://docs.astral.sh/uv/) and a C++ toolchain for CmdStan.

## Use

```
/bayesian-workflow:setup                  # once per project: Python env + CmdStan
/bayesian-workflow:run <data file>
/bayesian-workflow:explore <data file>    # exploratory data analysis only
```
