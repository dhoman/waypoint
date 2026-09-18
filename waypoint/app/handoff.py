"""Terminal operator interface; ownership and resume rules belong to runtime."""

import asyncio


async def interact(runner, surface, result):
    while result.status == "awaiting_intervention":
        token = surface.ownership.token
        print(
            f"PAUSED {runner.trace.run_id} at {runner.transition}: {result.reason}",
            flush=True,
        )
        print(f"Commands: take {token} | resume {token} | cancel", flush=True)
        while surface.ownership.state != "automation":
            try:
                parts = (await asyncio.to_thread(input, "control> ")).strip().split()
                if parts == ["cancel"]:
                    return runner.cancel()
                if parts == ["take", token]:
                    runner.take_control(token)
                    print("Human owns this surface.", flush=True)
                elif parts == ["resume", token]:
                    if not await runner.resume(token):
                        print(
                            "Resume rejected; restore an allowed checkpoint and identity.",
                            flush=True,
                        )
                else:
                    print("Invalid or stale command.", flush=True)
            except EOFError:
                return runner.cancel()
            except ValueError as exc:
                print(str(exc), flush=True)
        result = await runner.run()
    return result
