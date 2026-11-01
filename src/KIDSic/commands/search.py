"""Exercise the search service from the command line without an MCP client."""
import argparse
import asyncio
import json

from KIDSic.config.settings import Settings
from KIDSic.services.dependency import DependencyService


async def run(question: str):
    async with DependencyService(Settings.from_env()).kindergarten_search_service() as service:
        return await service.recommend(question)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Search stored kindergarten data and retrieve source evidence.')
    parser.add_argument('question', help='Croatian request containing age and city.')
    args = parser.parse_args(argv)
    print(json.dumps(asyncio.run(run(args.question)), ensure_ascii=False, default=str, indent=2))
