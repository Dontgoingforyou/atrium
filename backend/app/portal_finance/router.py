from fastapi import APIRouter

from app.portal_finance.routes.contracts import router as contracts_router
from app.portal_finance.routes.counterparties import router as counterparties_router
from app.portal_finance.routes.invoices import router as invoices_router
from app.portal_finance.routes.payments import router as payments_router
from app.portal_finance.routes.procurement import router as procurement_router

router = APIRouter(prefix="/portal/finance")
router.include_router(counterparties_router)
router.include_router(contracts_router)
router.include_router(invoices_router)
router.include_router(payments_router)
router.include_router(procurement_router)
