# -*- coding: utf-8 -*-
from fastapi import APIRouter

from .health import router as health_router
from .sync import router as sync_router
from .cron import router as cron_router
from .tracing import router as tracing_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(sync_router, tags=["sync"])
api_router.include_router(cron_router, tags=["cron"])
api_router.include_router(tracing_router, tags=["tracing"])
