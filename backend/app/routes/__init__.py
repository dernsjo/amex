from fastapi import APIRouter

from . import accounts, households, imports, me, transactions

router = APIRouter()
for module in (me, households, accounts, imports, transactions):
    router.include_router(module.router)
