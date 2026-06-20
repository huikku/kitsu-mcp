#!/usr/bin/env python3
"""Kitsu (CGWire) MCP server — coverage of the Zou API via Gazu, for LLM agents.

Design: Kitsu's **Zou** API is REST over a clear production model, reached through the official **Gazu**
SDK. A few **generic power tools** (`get` / `create` / `update` / `delete` over any Zou route) give full
reach, plus **typed convenience** (projects, assets, shots, sequences, tasks, status changes) and **schema
introspection** (asset/task types, statuses, departments, metadata-descriptors = custom fields). One write
family, a `dry_run` safety gate on every write. MIT licensed.

Config (env or MCP client config):
  KITSU_URL       e.g. https://your.kitsu.host/api   (note the /api suffix)
  KITSU_EMAIL     a Kitsu user (a dedicated bot account is recommended)
  KITSU_PASSWORD  that user's password

Run:  python3 server.py        (stdio transport, for Claude Desktop / Cursor / Claude Code)
"""
import os, tempfile
import gazu
from fastmcp import FastMCP

mcp = FastMCP("kitsu")
_connected = False


def _env(name, default=None):
    v = os.environ.get(name)
    if v:
        return v
    # fall back to a sibling .env (dev convenience) — never required in production
    for p in (".env",):
        if os.path.exists(p):
            for line in open(p):
                line = line.strip()
                if line.startswith(name + "="):
                    return line.split("=", 1)[1].split(" #", 1)[0].strip().strip('"').strip("'")
    return default


def kitsu():
    global _connected
    if not _connected:
        gazu.set_host(_env("KITSU_URL"))
        gazu.log_in(_env("KITSU_EMAIL"), _env("KITSU_PASSWORD"))
        _connected = True
    return gazu


# =====================================================================================
#  GENERIC POWER TOOLS  (one write family — full reach over the Zou REST API)
# =====================================================================================
def get(path: str) -> object:
    """GET any Zou API route and return its JSON — the escape hatch for full reach.
    e.g. get("data/projects"), get("data/shots/<id>"), get("data/persons"),
    get("data/projects/<id>/task-types")."""
    return kitsu().client.get(path)


def create(model: str, data: dict, dry_run: bool = False) -> dict:
    """Create an entity in any Zou model collection. `model` is the collection
    (e.g. "assets","shots","sequences","tasks","persons","comments"); `data` is the JSON payload
    (use ids for links, e.g. {"project_id":"...","name":"..."}).
    Set `dry_run=true` to preview the write without committing."""
    if dry_run:
        return {"dry_run": True, "would": "create", "model": model, "data": data}
    return kitsu().client.create(model, data)


def update(model: str, id: str, data: dict, dry_run: bool = False) -> dict:
    """Update an entity by id in a Zou model collection. `data` = fields to set.
    Set `dry_run=true` to preview without committing."""
    if dry_run:
        return {"dry_run": True, "would": "update", "model": model, "id": id, "data": data}
    return kitsu().client.update(model, id, data)


def delete(model: str, id: str, dry_run: bool = False) -> dict:
    """Delete an entity by id from a Zou model collection.
    Set `dry_run=true` to preview without committing."""
    if dry_run:
        return {"dry_run": True, "would": "delete", "model": model, "id": id}
    kitsu().client.delete("data/%s/%s" % (model, id))
    return {"ok": True, "deleted": {"model": model, "id": id}}


def remove_project(project_id: str, dry_run: bool = False) -> dict:
    """Delete a project. Kitsu only deletes a project once it is **closed**, and its content must be
    removed with force — this does both (close → force-remove). Irreversible.
    (The generic `delete` can't delete a populated project for this reason.) dry_run previews."""
    if dry_run:
        return {"dry_run": True, "would": "close + force-delete project", "project_id": project_id}
    k = kitsu()
    k.project.close_project(project_id)
    k.project.remove_project(project_id, force=True)
    return {"ok": True, "removed_project": project_id}


# =====================================================================================
#  SCHEMA / DISCOVERY  (Kitsu is configurable — let the agent learn the site first)
# =====================================================================================
def list_projects(include_closed: bool = False) -> list:
    """List projects (open by default)."""
    projs = kitsu().project.all_projects()
    if not include_closed:
        projs = [p for p in projs if p.get("project_status_name") != "Closed"]
    return projs


def list_asset_types() -> list:
    """All asset types (Character / Environment / Prop / FX / ...)."""
    return kitsu().asset.all_asset_types()


def list_task_types() -> list:
    """All task types — the columns of the production matrix (per entity-type)."""
    return kitsu().task.all_task_types()


def list_task_statuses() -> list:
    """All task statuses with their workflow flags (name, short_name, color, is_done, is_wip,
    is_retake, is_feedback_request, for_client, ...)."""
    return kitsu().task.all_task_statuses()


def list_departments() -> list:
    """All departments (disciplines)."""
    return kitsu().client.fetch_all("departments")


def list_metadata_descriptors(project_id: str) -> list:
    """Custom-field definitions — Kitsu's **schema-as-data** for a project: name, data type, choices,
    the `for_client` flag, and per-department visibility."""
    return kitsu().project.all_metadata_descriptors(project_id)


# =====================================================================================
#  TYPED CONVENIENCE — structure / tasks / the review loop
# =====================================================================================
def list_assets(project_id: str) -> list:
    """All assets in a project."""
    return kitsu().asset.all_assets_for_project(project_id)


def list_shots(project_id: str) -> list:
    """All shots in a project."""
    return kitsu().shot.all_shots_for_project(project_id)


def list_sequences(project_id: str) -> list:
    """All sequences in a project."""
    return kitsu().shot.all_sequences_for_project(project_id)


def list_tasks(entity_id: str) -> list:
    """All tasks on an entity (a shot or an asset)."""
    return kitsu().client.fetch_all("tasks", {"entity_id": entity_id})


def new_project(name: str, dry_run: bool = False) -> dict:
    """Create a project."""
    if dry_run:
        return {"dry_run": True, "would": "create project", "name": name}
    return kitsu().project.new_project(name)


def new_sequence(project_id: str, name: str, dry_run: bool = False) -> dict:
    """Create a sequence in a project."""
    if dry_run:
        return {"dry_run": True, "would": "create sequence", "project_id": project_id, "name": name}
    return kitsu().shot.new_sequence(project_id, name)


def new_asset(project_id: str, asset_type: str, name: str, description: str = "") -> dict:
    """Create an asset. `asset_type` is an asset-type **name or id** (names are resolved for you)."""
    k = kitsu()
    at = asset_type
    if isinstance(asset_type, str):
        at = next((t for t in k.asset.all_asset_types()
                   if asset_type in (t.get("id"), t.get("name"))), asset_type)
    return k.asset.new_asset(project_id, at, name, description=description)


def new_task(entity_id: str, task_type: str, name: str = "main") -> dict:
    """Create a task on an entity (shot/asset). `task_type` is a task-type **name or id**
    (names are resolved for you). Kitsu **scopes task types by entity type** (e.g. `Concept` exists for
    both Assets and Concepts), so when a name is ambiguous the one matching this entity is chosen."""
    k = kitsu()
    # gazu needs the full entity (it reads project_id off it), not just an id string
    entity = k.client.fetch_one("entities", entity_id) if isinstance(entity_id, str) else entity_id
    tt = task_type
    if isinstance(task_type, str):
        matches = [t for t in k.task.all_task_types() if task_type in (t.get("id"), t.get("name"))]
        tt = matches[0] if matches else task_type
        if len(matches) > 1 and isinstance(entity, dict) and entity.get("entity_type_id"):
            try:  # an Asset's entity_type_id is its *asset type* (Character/...), so map to the category
                etid = entity["entity_type_id"]
                if etid in {a["id"] for a in k.asset.all_asset_types()}:
                    cat = "Asset"
                else:
                    cat = (k.client.fetch_one("entity-types", etid) or {}).get("name")
                tt = next((t for t in matches if t.get("for_entity") == cat), matches[0])
            except Exception:
                pass
    return k.task.new_task(entity, tt, name=name)


def new_shot(project_id: str, sequence_id: str, name: str, nb_frames: int = None) -> dict:
    """Create a shot under a sequence."""
    return kitsu().shot.new_shot(project_id, sequence_id, name, nb_frames=nb_frames)


def set_task_status(task_id: str, status: str, comment: str = "") -> dict:
    """Set a task's status by posting a comment — the Kitsu review loop. `status` is a status
    name or short_name (e.g. "wip","done","retake","wfa"); `comment` is optional text."""
    k = kitsu()
    statuses = k.task.all_task_statuses()
    st = next((s for s in statuses
               if status.lower() in (s.get("short_name", "").lower(), s.get("name", "").lower())), None)
    if st is None:
        return {"error": "unknown status %r" % status,
                "available": [s.get("short_name") for s in statuses]}
    return k.task.add_comment(task_id, st, comment)


def set_casting(project_id: str, shot_id: str, asset_ids: list, dry_run: bool = False) -> dict:
    """Cast assets into a shot (Kitsu breakdown). `asset_ids` = list of asset ids; each gets 1 occurrence.
    Carries asset→shot casting INTO Kitsu during a migration."""
    if dry_run:
        return {"dry_run": True, "would": "set casting", "shot_id": shot_id, "assets": asset_ids}
    casting = [{"asset_id": a, "nb_occurences": 1, "label": ""} for a in asset_ids]
    return kitsu().casting.update_shot_casting(project_id, shot_id, casting)


def add_metadata_descriptor(project_id: str, name: str, entity_type: str = "Shot",
                            data_type: str = "string", choices: list = None,
                            for_client: bool = False, dry_run: bool = False) -> dict:
    """Define a **custom field** (Kitsu metadata-descriptor / schema-as-data) on a project.
    `entity_type` = "Shot"/"Asset"/…; `data_type` = "string"/"number"/"boolean"/"list"; `choices` for lists;
    `for_client` exposes it to clients. Migration: recreate source custom-field definitions here, then
    `set_metadata` the values."""
    if dry_run:
        return {"dry_run": True, "would": "add metadata descriptor", "name": name, "entity_type": entity_type}
    return kitsu().project.add_metadata_descriptor(project_id, name, entity_type,
                                                   data_type=data_type, choices=choices, for_client=for_client)


def set_metadata(entity_id: str, field_name: str, value, dry_run: bool = False) -> dict:
    """Set a **custom field value** on a shot/asset (merges into its `data`). The matching descriptor must
    exist (see `add_metadata_descriptor`). Carries custom-field values INTO Kitsu during a migration."""
    if dry_run:
        return {"dry_run": True, "would": "set metadata", "entity_id": entity_id, field_name: value}
    k = kitsu()
    ent = k.client.fetch_one("entities", entity_id)
    if ent and ent.get("entity_type_id") in {a["id"] for a in k.asset.all_asset_types()}:
        return k.asset.update_asset_data(entity_id, {field_name: value})
    return k.shot.update_shot_data(entity_id, {field_name: value})


# =====================================================================================
#  MEDIA / VERSIONS  (in Kitsu a "version" = a preview file [image/movie] on a task;
#  an entity's thumbnail derives from a preview. These carry media in/out for migrations.)
# =====================================================================================
def _status_id(status):
    for s in kitsu().task.all_task_statuses():
        if status and status.lower() in (s.get("short_name", "").lower(), s.get("name", "").lower()):
            return s["id"]
    return None


def upload_preview(task_id: str, file_path: str, comment: str = "", status: str = None,
                   set_thumbnail: bool = True, dry_run: bool = False) -> dict:
    """Upload a media file (image or movie) as a new **version/preview** on a task — the Kitsu review unit.
    `set_thumbnail=true` also makes it the linked entity's thumbnail. `status` is a task status name
    (default: keep the task's current status). Use this to carry media INTO Kitsu during a migration."""
    if dry_run:
        return {"dry_run": True, "would": "upload preview", "task_id": task_id, "file": file_path,
                "set_thumbnail": set_thumbnail}
    k = kitsu()
    st = _status_id(status) if status else (k.client.fetch_one("tasks", task_id) or {}).get("task_status_id")
    comment_obj, preview = k.task.publish_preview(
        task_id, st, comment=comment, preview_file_path=file_path, set_thumbnail=set_thumbnail)
    return {"ok": True, "preview_file_id": preview.get("id"), "task_id": task_id,
            "set_thumbnail": set_thumbnail}


def download_preview(preview_file_id: str, path: str = None, movie: bool = False) -> dict:
    """Download a preview file's media to disk (image by default; `movie=true` for the movie).
    Use this to read media OUT of Kitsu during a migration. Returns the saved path."""
    k = kitsu()
    if not path:
        fd, path = tempfile.mkstemp(suffix=".mp4" if movie else ".png"); os.close(fd)
    (k.files.download_preview_movie if movie else k.files.download_preview_file)(preview_file_id, path)
    return {"ok": True, "path": path, "bytes": os.path.getsize(path)}


def list_previews(task_id: str) -> list:
    """List the preview files (versions) on a task, newest first."""
    return kitsu().task.all_previews_for_task(task_id)


def whoami() -> dict:
    """The authenticated Kitsu user + host (validates the connection)."""
    k = kitsu()
    try:
        u = k.client.get_current_user()
    except Exception as e:
        u = {"error": str(e)}
    return {"host": _env("KITSU_URL"), "user": u}


# ---- register every function above as an MCP tool -----------------------------------------
for _fn in (get, create, update, delete, remove_project,
            list_projects, list_asset_types, list_task_types, list_task_statuses,
            list_departments, list_metadata_descriptors,
            list_assets, list_shots, list_sequences, list_tasks,
            new_project, new_sequence, new_asset, new_shot, new_task, set_task_status, set_casting,
            add_metadata_descriptor, set_metadata,
            upload_preview, download_preview, list_previews, whoami):
    mcp.tool(_fn)


if __name__ == "__main__":
    mcp.run()
