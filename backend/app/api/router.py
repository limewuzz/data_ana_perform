from fastapi import APIRouter

from app.api.routes import annotations, auth, export, model_configs, models, queue, review_sets, stats, tasks, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(models.router)
api_router.include_router(tasks.router)
api_router.include_router(annotations.router)
api_router.include_router(queue.router)
api_router.include_router(export.router)
api_router.include_router(model_configs.router)
api_router.include_router(stats.router)
api_router.include_router(review_sets.router)
api_router.include_router(users.router)
