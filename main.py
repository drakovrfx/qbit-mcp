import os
from typing import Any
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

    # Start search
    search_job = client.search_start(pattern=query, plugins=plugins, category=category)

    # Get search job ID
    search_id = search_job.id

    # Wait for results (check status until complete or timeout)
    import time
    max_wait = 30  # seconds
    waited = 0

    while waited < max_wait:
        status = client.search_status(search_id=search_id)
        if status[0].status == "Stopped":
            break
        time.sleep(1)
        waited += 1

    # Get results
    results = client.search_results(search_id=search_id, limit=100)

    # Stop search
    client.search_delete(search_id=search_id)

    # Format results
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
        category: Category to assign to the torrent (optional)
        tags: Comma-separated tags to assign (optional)
        paused: Start torrent in paused state (default: False)

    Returns:
        Status information about the download
    """
    client = get_qbt_client()

    # Prepare options
    options = {}
    if save_path:
        options["savepath"] = save_path
    if category:
        options["category"] = category
    if tags:
        options["tags"] = tags
    if paused:
        options["paused"] = "true"

    # Add torrent
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
def get_torrent_info(torrent_hash: str = None) -> list[dict[str, Any]]:
    """
    Get information about torrents in qBittorrent.

    Args:
        torrent_hash: Specific torrent hash to get info for (optional, returns all if not provided)

    Returns:
        List of torrent information
    """
    client = get_qbt_client()

    if torrent_hash:
        torrents = client.torrents_info(torrent_hashes=torrent_hash)
    else:
        torrents = client.torrents_info()

    result = []
    for torrent in torrents:
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
            "save_path": torrent.save_path
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
