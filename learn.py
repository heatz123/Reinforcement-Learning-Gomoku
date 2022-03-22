import asyncio

from arena import AIVAIArena


async def new_arena():
    arena = AIVAIArena()
    await arena.start_game()
    # TODO


if __name__ == '__main__':
    print('Learning mode')
    asyncio.run(new_arena())
