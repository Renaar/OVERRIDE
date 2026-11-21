"""FastAPI app: JSON API + static front-end."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Body, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import settings as S
from .service import Game, GameError, ensure_data_files, today

game: Game | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global game
    ensure_data_files()
    game = Game(S.DATA_DIR, S.DB_PATH)
    yield


app = FastAPI(title=S.APP_NAME, lifespan=lifespan, docs_url=None, redoc_url=None)


@app.exception_handler(GameError)
async def game_error(_: Request, exc: GameError):
    return JSONResponse({"detail": str(exc)}, status_code=exc.status)


def run(fn, *args):
    with game.connect() as con:
        return fn(con, *args)


@app.get("/healthz")
def healthz():
    with game.connect() as con:
        con.execute("SELECT 1")
    return {"status": "ok", "app": S.APP_NAME, "version": S.APP_VERSION}


@app.get("/api/state")
def state():
    return run(game.state, today())


@app.get("/api/summary")
def summary():
    return run(game.summary, today())


@app.post("/api/awakening")
def awakening(data: dict = Body(...)):
    return run(game.awaken, data, today())


@app.post("/api/checkin")
def checkin(data: dict = Body(...)):
    return run(game.do_checkin, data, today())


@app.get("/api/quests/{qid}")
def quest(qid: int):
    return run(game.quest_plan, qid)


@app.post("/api/quests/{qid}/complete")
def complete(qid: int, data: dict = Body(...)):
    return run(game.complete, qid, data, today())


@app.get("/api/skills")
def skills():
    return run(game.skills_view, today())


@app.get("/api/inventory")
def inventory():
    return run(game.inventory_view)


@app.get("/api/journal")
def journal(limit: int = 200):
    return run(game.journal, min(limit, 1000))


@app.get("/api/settings")
def get_settings():
    return run(game.settings)


@app.put("/api/settings")
def put_settings(data: dict = Body(...)):
    return run(game.set_settings, data)


# ---------------------------------------------------------------- front-end

@app.get("/")
def index():
    return FileResponse(S.WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})


app.mount("/", StaticFiles(directory=S.WEB_DIR), name="web")
