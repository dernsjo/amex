from fastapi import APIRouter

from . import accounts, categories, households, imports, me, transactions

router = APIRouter()
for module in (me, households, accounts, imports, transactions, categories):
    router.include_router(module.router)
