from fastapi import Header, HTTPException

from config import settings


def verify_worker_key(x_api_key: str = Header(default="")):
    if x_api_key != settings.worker_api_key:
        raise HTTPException(status_code=401, detail="Invalid worker API key")
    return True
