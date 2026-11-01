from fastapi import APIRouter

from . import accounts, analysis, categories, households, imports, me, transactions

router = APIRouter()
for module in (me, households, accounts, imports, transactions, categories, analysis):
    router.include_router(module.router)
