from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time
import uuid

import jwt
from pydantic import BaseModel
from fastapi.responses import JSONResponse

import os
import yaml
from dotenv import dotenv_values
from fastapi import Query

app = FastAPI()

ALLOWED_ORIGIN = "https://dash-imw15r.example.com"
EMAIL = "24f1000791@ds.study.iitm.ac.in"

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----"""

ISSUER = "https://idp.exam.local"
AUDIENCE = "tds-wwoh3luq.apps.exam.local"

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        response.headers["X-Request-ID"] = str(uuid.uuid4())
        response.headers["X-Process-Time"] = f"{elapsed:.6f}"
        return response

app.add_middleware(TimingMiddleware)

@app.get("/stats")
async def stats(values: str = Query(...)):
    nums = [int(x.strip()) for x in values.split(",") if x.strip()]

    return {
        "email": EMAIL,
        "count": len(nums),
        "sum": sum(nums),
        "min": min(nums),
        "max": max(nums),
        "mean": sum(nums) / len(nums),
    }

class VerifyRequest(BaseModel):
    token: str


@app.post("/verify")
async def verify(req: VerifyRequest):
    try:
        payload = jwt.decode(
            req.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        return {
            "valid": True,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
        }

    except Exception:
        return JSONResponse(
            status_code=401,
            content={"valid": False},
        )

def to_bool(value):
    return str(value).lower() in ("true", "1", "yes", "on")


@app.get("/effective-config")
async def effective_config(set: list[str] = Query(default=[])):
    config = {
        "port": 8000,
        "workers": 1,
        "debug": False,
        "log_level": "info",
        "api_key": "default-secret-000",
    }

    # YAML
    if os.path.exists("config.development.yaml"):
        with open("config.development.yaml") as f:
            config.update(yaml.safe_load(f) or {})

    # .env
    env = dotenv_values(".env")

    if "APP_PORT" in env:
        config["port"] = int(env["APP_PORT"])

    if "NUM_WORKERS" in env:
        config["workers"] = int(env["NUM_WORKERS"])

    if "APP_LOG_LEVEL" in env:
        config["log_level"] = env["APP_LOG_LEVEL"]

    if "APP_API_KEY" in env:
        config["api_key"] = env["APP_API_KEY"]

    # OS Environment
    if os.getenv("APP_PORT"):
        config["port"] = int(os.getenv("APP_PORT"))

    if os.getenv("APP_WORKERS"):
        config["workers"] = int(os.getenv("APP_WORKERS"))

    if os.getenv("APP_LOG_LEVEL"):
        config["log_level"] = os.getenv("APP_LOG_LEVEL")

    if os.getenv("APP_API_KEY"):
        config["api_key"] = os.getenv("APP_API_KEY")

    # CLI overrides
    for item in set:
        if "=" not in item:
            continue

        key, value = item.split("=", 1)

        if key == "port":
            config["port"] = int(value)
        elif key == "workers":
            config["workers"] = int(value)
        elif key == "debug":
            config["debug"] = to_bool(value)
        else:
            config[key] = value

    config["api_key"] = "****"

    return config