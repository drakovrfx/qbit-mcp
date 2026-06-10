import os
import time
import datetime
from typing import Any, Optional
from fastmcp import FastMCP
import qbittorrentapi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("qBittorrent MCP Server")

# qBittorrent client instance (will be initialized on first use)
qbt_client = None


def get_qbt_client():
    """Get or create qBittorrent client instance."""
    global qbt_client

    if qbt_client is None:
        host = os.getenv("QBITTORRENT_HOST", "http://localhost:8080")
        username = os.getenv("QBITTORRENT_USERNAME", "admin")
        password = os.getenv("QBITTORRENT_PASSWORD", "adminadmin")

        qbt_client = qbittorrentapi.Client(
            host=host,
            username=username,
            password=password
        )

        try:
            qbt_client.auth_log_in()
        except qbittorrentapi.LoginFailed as e:
            raise Exception(f"Failed to login to qBittorrent: {e}")

    return qbt_client


@mcp.tool()
def search_torrents(query: str, plugins: str = "all", category: str = "all") -> list[dict[str, Any]]:
    """
    Search for torrents using qBittorrent's search plugins.

    Args:
        query: Search query string
        plugins: Comma-separated list of plugin names or "all" for all enabled plugins
        category: Filter by category (all, movies, tv, music, games, anime, software, pictures, books)

    Returns:
        List of search results with torrent information
    """
    client = get_qbt_client()

    search_job = client.search_start(pattern=query, plugins=plugins, category=category)
    search_id = search_job.id

    max_wait = 30
    waited = 0

    while waited < max_wait:
        status = client.search_status(search_id=search_id)
        if status[0].status == "Stopped":
            break
        time.sleep(1)
        waited += 1

    results = client.search_results(search_id=search_id, limit=100)
    client.search_delete(search_id=search_id)

    formatted_results = []
    for result in results.results:
        formatted_results.append({
            "name": result.fileName,
            "size": result.fileSize,
            "size_readable": f"{result.fileSize / (1024**3):.2f} GB",
            "seeders": result.nbSeeders,
            "leechers": result.nbLeechers,
            "url": result.fileUrl,
            "description_url": result.descrLink,
            "site": result.siteUrl
        })

    return formatted_results


@mcp.tool()
def download_torrent(
    url: str,
    save_path: str = None,
    category: str = None,
    tags: str = None,
    paused: bool = False
) -> dict[str, Any]:
    """
    Download a torrent by URL or magnet link.

    Args:
        url: Torrent URL or magnet link
        save_path: Directory to save the torrent (optional)
        category: Category to assign to the torrent — use this to route to the correct folder (optional)
        tags: Comma-separated tags to assign (optional)
        paused: Start torrent in paused state (default: False)

    Returns:
        Status information about the download
    """
    client = get_qbt_client()

    options = {}
    if save_path:
        options["savepath"] = save_path
    if category:
        options["category"] = category
    if tags:
        options["tags"] = tags
    if paused:
        options["paused"] = "true"

    try:
        result = client.torrents_add(urls=url, **options)

        if result == "Ok.":
            return {
                "status": "success",
                "message": "Torrent added successfully",
                "url": url
            }
        else:
            return {
                "status": "error",
                "message": f"Failed to add torrent: {result}",
                "url": url
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error adding torrent: {str(e)}",
            "url": url
        }


@mcp.tool()
def get_torrent_info(
    torrent_hash: Optional[str] = None,
    filter: Optional[str] = None,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort: Optional[str] = None,
    reverse: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Get information about torrents in qBittorrent.

    Args:
        torrent_hash: Specific torrent hash (optional, returns all if not provided)
        filter: Filter by state. Options: all, downloading, seeding, completed,
                paused, active, inactive, resumed, stalled, stalled_uploading,
                stalled_downloading, errored (optional)
        category: Filter by category name (optional, use empty string "" for uncategorised)
        tag: Filter by tag name (optional, use empty string "" for untagged)
        sort: Field to sort by, e.g. "last_activity", "added_on", "ratio",
              "size", "name", "state" (optional)
        reverse: Reverse the sort order (default: False)
        limit: Maximum number of torrents to return — use this to avoid large
               responses. Recommended: 200 or less (optional)
        offset: Number of torrents to skip — combine with limit for pagination,
                e.g. offset=0&limit=200, then offset=200&limit=200 (optional)

    Returns:
        List of torrent information. Total count is included as the first element
        when using limit/offset so you know how many pages to expect.
    """
    client = get_qbt_client()

    # Build kwargs — only pass params that are explicitly set,
    # so we don't override qBittorrent defaults with None values
    kwargs = {}
    if torrent_hash:
        kwargs["torrent_hashes"] = torrent_hash
    if filter:
        kwargs["status_filter"] = filter
    if category is not None:          # allow empty string for "no category"
        kwargs["category"] = category
    if tag is not None:               # allow empty string for "no tag"
        kwargs["tag"] = tag
    if sort:
        kwargs["sort"] = sort
    if reverse:
        kwargs["reverse"] = reverse
    if limit is not None:
        kwargs["limit"] = limit
    if offset is not None:
        kwargs["offset"] = offset

    torrents = client.torrents_info(**kwargs)

    now = int(datetime.datetime.now().timestamp())
    result = []

    # When paginating, prepend a metadata entry so the caller knows
    # the total count without fetching everything
    if limit is not None or offset is not None:
        total = client.torrents_info(
            status_filter=filter or "all",
            category=category,
            tag=tag,
        )
        result.append({
            "_meta": True,
            "total_count": len(total),
            "returned_count": len(torrents),
            "offset": offset or 0,
            "limit": limit,
        })

    for torrent in torrents:
        added = torrent.added_on
        last_active = torrent.last_activity
        completed = getattr(torrent, "completion_on", None)
        seeding_time = getattr(torrent, "seeding_time", None)

        result.append({
            "hash": torrent.hash,
            "name": torrent.name,
            "size": torrent.size,
            "size_readable": f"{torrent.size / (1024**3):.2f} GB",
            "progress": f"{torrent.progress * 100:.2f}%",
            "state": torrent.state,
            "download_speed": f"{torrent.dlspeed / (1024**2):.2f} MB/s",
            "upload_speed": f"{torrent.upspeed / (1024**2):.2f} MB/s",
            "eta": torrent.eta,
            "seeders": torrent.num_seeds,
            "leechers": torrent.num_leechs,
            "ratio": torrent.ratio,
            "category": torrent.category,
            "tags": torrent.tags,
            "save_path": torrent.save_path,
            "added_on": added,
            "added_on_readable": datetime.datetime.fromtimestamp(added).strftime('%Y-%m-%d') if added else "unknown",
            "last_activity": last_active,
            "last_activity_readable": datetime.datetime.fromtimestamp(last_active).strftime('%Y-%m-%d') if last_active else "unknown",
            "days_since_activity": int((now - last_active) / 86400) if last_active else None,
            "completion_on": completed,
            "completion_on_readable": datetime.datetime.fromtimestamp(completed).strftime('%Y-%m-%d') if completed else None,
            "seeding_time_days": round(seeding_time / 86400, 1) if seeding_time else None,
        })

    return result


@mcp.tool()
def list_search_plugins() -> list[dict[str, Any]]:
    """
    List all available search plugins in qBittorrent.

    Returns:
        List of search plugins with their status
    """
    client = get_qbt_client()

    plugins = client.search_plugins()

    result = []
    for plugin in plugins:
        result.append({
            "name": plugin.name,
            "version": plugin.version,
            "enabled": plugin.enabled,
            "url": plugin.url,
            "supported_categories": plugin.supportedCategories
        })

    return result


@mcp.tool()
def pause_torrent(torrent_hash: str) -> dict[str, str]:
    """
    Pause a torrent.

    Args:
        torrent_hash: Hash of the torrent to pause

    Returns:
        Status message
    """
    client = get_qbt_client()

    try:
        client.torrents_pause(torrent_hashes=torrent_hash)
        return {"status": "success", "message": f"Torrent {torrent_hash} paused"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def resume_torrent(torrent_hash: str) -> dict[str, str]:
    """
    Resume a paused torrent.

    Args:
        torrent_hash: Hash of the torrent to resume

    Returns:
        Status message
    """
    client = get_qbt_client()

    try:
        client.torrents_resume(torrent_hashes=torrent_hash)
        return {"status": "success", "message": f"Torrent {torrent_hash} resumed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def delete_torrent(torrent_hash: str, delete_files: bool = False) -> dict[str, str]:
    """
    Delete a torrent from qBittorrent.

    Args:
        torrent_hash: Hash of the torrent to delete
        delete_files: Also delete downloaded files (default: False)

    Returns:
        Status message
    """
    client = get_qbt_client()

    try:
        client.torrents_delete(delete_files=delete_files, torrent_hashes=torrent_hash)
        return {
            "status": "success",
            "message": f"Torrent {torrent_hash} deleted (files deleted: {delete_files})"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    mcp.run()
