from fastapi import APIRouter

from . import accounts, households, me, transactions

router = APIRouter()
for module in (me, households, accounts, transactions):
    router.include_router(module.router)
