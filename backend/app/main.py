import os
from contextlib import asynccontextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .database import Base, build_database
from .routers.api import router
from .services.rates import fetch_rates


def local_today():
    return datetime.now(ZoneInfo('Asia/Shanghai')).date()


def create_app(db_path=None, today_provider=None, rates_fetcher=None):
    engine, session_factory = build_database(db_path)
    Base.metadata.create_all(engine)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title='财富自由之路 API', version='1.0.0', lifespan=lifespan)
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.today_provider = today_provider or local_today
    app.state.rates_fetcher = rates_fetcher or fetch_rates
    app.state.rates_last_attempt = None
    origins = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',')
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type'])

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Avoid echoing non-finite JSON values or exception objects in the body.
        details = '; '.join(f"{'.'.join(map(str, error['loc'][1:]))}: {error['msg']}" for error in exc.errors())
        return JSONResponse(status_code=422, content={'detail': details})

    @app.exception_handler(IntegrityError)
    async def conflict(request: Request, exc: IntegrityError):
        return JSONResponse(status_code=409, content={'detail': '该操作与已有记录冲突，请刷新页面后重试'})

    app.include_router(router)
    return app


app = create_app()
