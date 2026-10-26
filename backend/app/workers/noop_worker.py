import asyncio


async def handle_noop(ctx, db_session, job_id: str, job_kwargs: dict):
    # This is a placeholder task
    await asyncio.sleep(1)
    return {"status": "succeeded", "message": "No-op task completed successfully."}
