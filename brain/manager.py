"""Stub manager that will later schedule sub-agents."""
import asyncio

async def main():
    while True:
        await asyncio.sleep(600)  # placeholder loop

if __name__ == "__main__":
    asyncio.run(main()) 