from datetime import datetime

import httpx

# Timeout confortável para Vercel Pro (60s por request)
_TIMEOUT = 15.0


async def fetch_comments_page(
    video_id: str,
    api_key: str,  # valor extraído do SecretStr — nunca logar esta variável
    max_results: int = 100,
    page_token: str | None = None,
) -> dict:
    params: dict = {
        "part": "snippet,replies",
        "videoId": video_id,
        "key": api_key,
        "maxResults": min(max_results, 100),
        "textFormat": "plainText",
    }
    if page_token:
        params["pageToken"] = page_token

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/commentThreads",
            params=params,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


async def fetch_video_info(video_id: str, api_key: str) -> dict | None:
    """Retorna o objeto de vídeo (snippet + statistics) ou None."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "snippet,statistics",
                "id": video_id,
                "key": api_key,
            },
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        items = response.json().get("items", [])
        return items[0] if items else None


async def fetch_replies_page(
    parent_id: str,
    api_key: str,
    page_token: str | None = None,
) -> dict:
    """Busca replies via comments.list (até 100 por página)."""
    params: dict = {
        "part": "snippet",
        "parentId": parent_id,
        "key": api_key,
        "maxResults": 100,
        "textFormat": "plainText",
    }
    if page_token:
        params["pageToken"] = page_token

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/comments",
            params=params,
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()


async def fetch_channels_info(
    channel_ids: list[str], api_key: str
) -> dict[str, datetime]:
    """
    Retorna {channel_id: published_at} para cada canal encontrado.
    Faz batches de até 50 IDs por chamada (limite da API).
    """
    result: dict[str, datetime] = {}
    async with httpx.AsyncClient() as client:
        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i : i + 50]
            response = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={
                    "part": "snippet",
                    "id": ",".join(batch),
                    "key": api_key,
                },
                timeout=_TIMEOUT,
            )
            response.raise_for_status()
            for item in response.json().get("items", []):
                published_at = item.get("snippet", {}).get("publishedAt")
                if published_at:
                    result[item["id"]] = datetime.fromisoformat(
                        published_at.replace("Z", "+00:00")
                    )
    return result


# IMPORTANTE: nunca passar api_key para logger, nunca incluir em mensagens de erro
