"""Web server: serves the UI and the /api/structure endpoint.

Run: uvicorn app:app --reload  →  http://localhost:8000
"""

from pathlib import Path

import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from structurer import StructureError, structure_text

STATIC = Path(__file__).parent / "static"
MAX_CHARS = 100_000

app = FastAPI(title="Ori - 글 구조화")


class StructureRequest(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_CHARS)


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.post("/api/structure")
async def structure(req: StructureRequest):
    try:
        return await run_in_threadpool(structure_text, req.text)
    except StructureError as e:
        raise HTTPException(422, str(e))
    except anthropic.AuthenticationError:
        raise HTTPException(500, "ANTHROPIC_API_KEY가 없거나 올바르지 않습니다.")
    except anthropic.RateLimitError:
        raise HTTPException(429, "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
    except anthropic.APIStatusError as e:
        raise HTTPException(502, f"Claude API 오류 ({e.status_code})")
    except anthropic.APIConnectionError:
        raise HTTPException(502, "Claude API에 연결할 수 없습니다.")
