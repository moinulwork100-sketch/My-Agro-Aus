from fastapi import HTTPException


def not_found(resource: str, id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{resource} '{id}' not found")


def server_error(detail: str = "Internal server error") -> HTTPException:
    return HTTPException(status_code=500, detail=detail)
