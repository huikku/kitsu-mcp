# Kitsu MCP server

A **Model Context Protocol** server that gives LLM agents (Claude Desktop, Claude Code, Cursor, …) access to
**[Kitsu](https://www.cg-wire.com/kitsu)** — CGWire's open-source production tracker — through its **Zou** API
and the official **[Gazu](https://github.com/cgwire/gazu)** SDK.

> **21 tools, one write family, a `dry_run` safety gate on every write.** Tested live against a self-hosted
> Kitsu — including a full **ShotGrid → Kitsu migration** (new project + sequence + shots + assets + tasks,
> verified and cleaned up).

Part of a small **tracker-MCP trio** — see [Migrating projects between platforms](#migrating-projects-between-platforms).

## The 21 tools
**Generic power tools (full reach over the Zou REST API):**
- `get` — GET any Zou route (the escape hatch)
- `create` · `update` · `delete` — write to any Zou model collection

**Schema & discovery (Kitsu is configurable — learn the site first):**
- `list_projects`
- `list_asset_types` · `list_task_types` · `list_task_statuses` (with workflow flags) · `list_departments`
- `list_metadata_descriptors` — Kitsu's **schema-as-data** custom fields (`for_client` + per-department)

**Typed convenience (structure, creation + the review loop):**
- `list_assets` · `list_shots` · `list_sequences` · `list_tasks`
- `new_project` · `new_sequence` · `new_asset` · `new_shot` · `new_task` (type names resolved for you)
- `set_task_status` — post a comment that sets a task's status (the Kitsu review loop)
- `whoami`

> The `new_*` builders make Kitsu a viable **migration target** — read structure from another tracker
> (e.g. `shotgrid-mcp`) and recreate the project here. See
> [Migrating projects between platforms](#migrating-projects-between-platforms).

`create`, `update`, `delete` each take `dry_run: bool = false` — set it `true` to preview the write and
commit nothing.

## Install
```bash
pip install -r requirements.txt        # fastmcp, gazu
```

## Configure (credentials)
| var | value |
|---|---|
| `KITSU_URL` | your Kitsu API base, **including `/api`** — e.g. `https://your.kitsu.host/api` |
| `KITSU_EMAIL` | a Kitsu user (a **dedicated bot account** is recommended) |
| `KITSU_PASSWORD` | that user's password |

For local dev you can drop them in a `.env` next to `server.py` (gitignored — see `.env.example`).

## Run / wire into a client
```bash
python3 server.py        # stdio transport
```
Claude Code:
```bash
claude mcp add kitsu \
  -e KITSU_URL=https://your.kitsu.host/api \
  -e KITSU_EMAIL=bot@studio.com -e KITSU_PASSWORD=•••• \
  -- python3 /path/to/kitsu-mcp/server.py
```

## Examples (what the agent calls)
```python
get("data/projects")                                   # raw route, full reach
list_shots("<project_id>")                             # typed convenience
list_task_statuses()                                   # workflow-as-data (is_done/for_client/…)
new_asset("<project_id>", "Character", "Hero")         # asset-type name resolved for you
set_task_status("<task_id>", "wip", "Starting blocking")
create("shots", {"project_id":"…","name":"sh010"}, dry_run=True)   # preview, commit nothing
```

## Migrating projects between platforms
This is one of **three sibling tracker MCPs**, each exposing the **same shape** (generic CRUD + schema +
typed convenience, with a `dry_run` gate):

| Tracker | MCP |
|---|---|
| ShotGrid / Flow Production Tracking | [`huikku/shotgrid-mcp`](https://github.com/huikku/shotgrid-mcp) |
| ftrack Studio | [`huikku/ftrack-mcp`](https://github.com/huikku/ftrack-mcp) |
| **Kitsu (CGWire)** | this repo |

Because all three speak the same production model (Project → Sequence/Asset → Shot → Task → Version/Status)
and present a uniform tool surface, **an agent with two of them loaded can migrate a project from one
platform to another** — read the structure from the source tracker, map the schema, and recreate it in the
target:

> *"Read every sequence, asset, shot and task from the ShotGrid project, then recreate them in Kitsu."*

The agent calls `find`/`list_*` on the source MCP and `create`/`new_*` on the target — no bespoke migration
script. (This trio grew out of exactly that exercise: a single project copied across ShotGrid, ftrack and
Kitsu to prove the tracker-agnostic, agent-native approach.)

## Credits
- **[Kitsu, Zou & Gazu](https://github.com/cgwire)** by **CGWire** — the open-source tracker, its API, and
  the Python SDK this is built on. Please support and star them.
- Companion to **[`shotgrid-mcp`](https://github.com/huikku/shotgrid-mcp)** and
  **[`ftrack-mcp`](https://github.com/huikku/ftrack-mcp)**.

MIT licensed.
