# Tracker comparison — ShotGrid · ftrack · Kitsu

These three MCP servers ([`shotgrid-mcp`](https://github.com/huikku/shotgrid-mcp),
[`ftrack-mcp`](https://github.com/huikku/ftrack-mcp), [`kitsu-mcp`](https://github.com/huikku/kitsu-mcp))
expose the **same shape** so an agent can read a project from one tracker and recreate it in another. This
doc compares the servers, shows how the platforms' data models line up, and — most importantly — lists the
**incompatibilities you hit when migrating between them**. Everything here was observed in **live round-trip
tests** (all six directions across the three trackers).

## 1. The MCP servers
| | shotgrid-mcp | ftrack-mcp | kitsu-mcp |
|---|---|---|---|
| Platform | ShotGrid / Flow Production Tracking | ftrack Studio | Kitsu (CGWire) |
| Backing SDK | `shotgun_api3` | `ftrack_api` | `gazu` → Zou REST |
| Auth | script name + API key | API user + API key | email + password |
| Tools | 15 | 28 | 22 |
| API shape | generic CRUD over a schema | generic query + CRUD over a schema | generic REST + typed helpers |
| Write safety | `dry_run` on writes | `dry_run` on writes | `dry_run` on writes |
| Entity ids | **integer** | **UUID string** | **UUID string** |
| License | MIT | MIT | MIT |

## 2. Data-model mapping (how the concepts line up)
| Concept | ShotGrid | ftrack | Kitsu |
|---|---|---|---|
| Project | `Project` | `Project` (needs a **schema**) | `Project` |
| Sequence | `Sequence` | `Sequence` | `Sequence` |
| Shot | `Shot` (`sg_sequence` link) | `Shot` (parent = Sequence) | `Shot` (`parent_id` = Sequence) |
| Asset | `Asset` (`sg_asset_type` string) | `AssetBuild` (typed) | `Asset` (asset-type entity) |
| Task | `Task` (+ pipeline **`Step`**) | `Task` (+ **`Type`**) | `Task` (+ **`task_type`**) |
| Task status | `sg_status_list` | `Status` (schema-scoped) | `task_status` |
| Casting (asset→shot) | `Shot.assets` (multi-entity) | **— none** (uses AssetVersion/links) | **breakdown / casting** (first-class) |
| Custom fields | `sg_*` schema fields | custom attributes (schema-as-data) | metadata-descriptors (schema-as-data) |
| Hierarchy | flat + links | strict parent tree (Context) | project → entity tree |

## 3. Status vocabularies — **no 1:1; you must map**
Each platform ships a different status set, so migration has to translate. The mapping these servers use:

| Meaning | Kitsu | ShotGrid | ftrack (VFX schema) |
|---|---|---|---|
| not started | `todo` | `wtg` | `Not started` |
| ready | `ready` | `wtg` | `Ready to start` |
| in progress | `wip` | `ip` | `In progress` |
| done / final | `done` | `fin` | *(no exact match)* → `In progress` |
| waiting for approval | `wfa` | `rev` | `Pending Review` |
| approved | `approved` | `apr` | *(no exact match)* → `Pending Review` |
| retake / revise | `retake` | `rev` | `Revise` |

> ⚠️ **ftrack's VFX schema has no clean "done"/"approved" *task* status**, so those collapse to the nearest
> review state when targeting ftrack. Round-tripping `done`/`approved` through ftrack is lossy.

## 4. Migration incompatibilities & gotchas (observed live)
- **Casting can't round-trip through ftrack.** Asset→shot casting is first-class in **Kitsu** (breakdown) and
  **ShotGrid** (`Shot.assets`), but **ftrack has no simple shot↔asset casting** — so casting only survives
  on SG↔Kitsu edges and is dropped when ftrack is the source or target.
- **Task types aren't universal.** e.g. Kitsu's **`Storyboard`** task type has no equivalent in ftrack's VFX
  schema, so those tasks are skipped when targeting ftrack. Map or pre-create task types first.
- **Asset types differ.** SG `sg_asset_type` is a free string; **ftrack `AssetBuild` requires a type from a
  fixed list** (no `FX` type → map `FX`→`Prop`); Kitsu asset types are named entities.
- **Project creation quirks:**
  - **ShotGrid:** API-created projects have **no UI navigation pages** unless `layout_project` (a template
    project) is set **at creation time**.
  - **ftrack:** a project **requires a schema** (VFX / Animation / Model / Video / Media) at creation.
  - **Kitsu:** a project can only be **deleted once *closed***, and its contents need a force-remove — the
    generic `delete` can't do it; use `remove_project` (close → force).
- **Name uniqueness:** **ftrack** enforces **case-insensitive, per-parent** name uniqueness (`FARMHOUSE` and
  `Farmhouse` collide; duplicate siblings fail). SG and Kitsu are more permissive.
- **Atomicity:** **ftrack** commits are **atomic** per `session.commit()` — one bad row fails the whole
  batch, so dedupe up front. SG and Kitsu commit per call.
- **Ids:** ShotGrid uses **integer** ids; ftrack and Kitsu use **UUID strings** — don't assume a type.

## 5. What these migrations carry today — and what they don't
| Data | Migrates? |
|---|---|
| Project / Sequence / Shot / Asset / Task structure | ✅ all directions |
| Task **statuses** (mapped per §3) | ✅ (lossy into ftrack, per above) |
| **Casting** (asset→shot) | ✅ on SG ↔ Kitsu; ❌ via ftrack |
| Frame ranges / cut durations | ✅ (where the field exists) |
| **Media / thumbnails / preview movies** | ❌ not yet |
| **Notes / comments / review history** | ❌ not yet |
| **Custom fields / metadata-descriptors** | ❌ not yet |
| **Time logs, Versions / Publishes** | ❌ not yet |

> **Scope note:** the cross-tracker tests were run on representative *slices* (a sequence + a few shots /
> assets / tasks), not full-scale projects. The structural + status + casting mechanics are proven in every
> direction; media/notes/custom-field carry-over is future work.

---
*Part of the tracker-MCP trio: [shotgrid-mcp](https://github.com/huikku/shotgrid-mcp) ·
[ftrack-mcp](https://github.com/huikku/ftrack-mcp) · [kitsu-mcp](https://github.com/huikku/kitsu-mcp). MIT.*
