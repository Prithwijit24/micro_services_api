from fastapi import FastAPI


def register_all_routers(app: FastAPI):
    from app.routers import (
        search,
        browse,
        embed,
        youtube,
        clip,
        reranker,
        graph,
        vector,
        cache,
        crawl,
        duckdb,
        storage,
        pipeline,
    )

    for module in [search, browse, embed, youtube, clip, reranker, graph, vector, cache, crawl, duckdb, storage, pipeline]:
        app.include_router(module.router)
