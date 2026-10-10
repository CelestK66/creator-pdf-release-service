from __future__ import annotations

import argparse
import asyncio
import os

from src.creator_release import AssetIngestion, CreatorDeliveryRequest, build_creator_delivery
from src.infrai_pdf import InfraiPdfClient


async def run(args: argparse.Namespace) -> None:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise SystemExit("Set INFRAI_API_KEY before running this script")

    request = CreatorDeliveryRequest(
        delivery_id=args.delivery_id,
        creator_id=args.creator_id,
        asset=AssetIngestion(asset_id=args.asset_id, template_html=args.template_html),
        template_vars={"creator_name": args.creator_name, "campaign_title": args.campaign_title},
    )
    client = InfraiPdfClient(api_key)
    try:
        delivery = await build_creator_delivery(request, client)
        print(delivery.model_dump_json(indent=2))
    finally:
        await client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a creator PDF release")
    parser.add_argument("--delivery-id", required=True)
    parser.add_argument("--creator-id", required=True)
    parser.add_argument("--asset-id", required=True)
    parser.add_argument("--template-html", required=True)
    parser.add_argument("--creator-name", required=True)
    parser.add_argument("--campaign-title", required=True)
    asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    main()
