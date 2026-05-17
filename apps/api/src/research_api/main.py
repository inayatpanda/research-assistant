from fastapi import FastAPI

app = FastAPI(title="Research Manuscript Assistant API")


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}
