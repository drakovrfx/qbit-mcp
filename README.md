# qBittorrent MCP Server

An MCP (Model Context Protocol) server that connects to qBittorrent's Web API to search and download torrents.

## Features

- **Search Torrents**: Search for torrents using qBittorrent's search plugins
- **Download Torrents**: Add torrents by URL or magnet link
- **Manage Torrents**: Get info, pause, resume, and delete torrents
- **List Plugins**: View available search plugins

## Prerequisites

1. **qBittorrent** with Web UI enabled
   - Download from [qbittorrent.org](https://www.qbittorrent.org/)
   - Enable Web UI in qBittorrent: `Tools > Options > Web UI`
   - Note your username, password, and port (default: 8080)

2. **Search Plugins** (for search functionality)
   - In qBittorrent: `View > Search Engine`
   - Click "Search plugins..." at bottom right
   - Install desired search plugins

## Installation

1. Open qbittorent and go into Options -> Webui -> Enable web interface, create login and set it up

2. Install qbittorent search plugins

3. Clone this repository:
```bash
git clone <repository-url>
cd qbit-mcp
```

4. Install dependencies:
```bash
pip install uv
```

5. Configure environment variables:
```bash
cp .env.example .env
```

Edit `.env` with your qBittorrent credentials:
```env
QBITTORRENT_HOST=http://localhost:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=your_password
```

## Usage

### Running the MCP Server

In witsy, click on the AC plug on the left panel, add a new server.

type: `stdio`

label: `qbit-mcp`

command: `uv`

arguments: `run --with fastmcp --with qbittorrent-api --with python-dotenv fastmcp run C:\directy\to\qbit-mcp\main.py`

Open a new Chat, click on the + sign and enable the qbit-mcp server.

Ask the LLM to download a torrent for you.

## Available Tools

### search_torrents
Search for torrents using qBittorrent's search plugins.

**Parameters:**
- `query` (string, required): Search query
- `plugins` (string, optional): Plugin names or "all" (default: "all")
- `category` (string, optional): Filter by category (default: "all")

**Example:**
```
Search for "ubuntu 24.04" torrents
```

### download_torrent
Download a torrent by URL or magnet link.

**Parameters:**
- `url` (string, required): Torrent URL or magnet link
- `save_path` (string, optional): Directory to save the torrent
- `category` (string, optional): Category to assign
- `tags` (string, optional): Comma-separated tags
- `paused` (boolean, optional): Start paused (default: false)

**Example:**
```
Download torrent from magnet:?xt=urn:btih:...
```

### get_torrent_info
Get information about torrents in qBittorrent.

**Parameters:**
- `torrent_hash` (string, optional): Specific torrent hash (returns all if not provided)

**Example:**
```
Show all torrents currently downloading
```

### list_search_plugins
List all available search plugins.

**Example:**
```
What search plugins are available?
```

### pause_torrent
Pause a torrent.

**Parameters:**
- `torrent_hash` (string, required): Hash of the torrent

### resume_torrent
Resume a paused torrent.

**Parameters:**
- `torrent_hash` (string, required): Hash of the torrent

### delete_torrent
Delete a torrent from qBittorrent.

**Parameters:**
- `torrent_hash` (string, required): Hash of the torrent
- `delete_files` (boolean, optional): Also delete files (default: false)

## Troubleshooting

### Connection Issues
- Verify qBittorrent Web UI is enabled and running
- Check that the host, port, username, and password are correct
- Ensure no firewall is blocking the connection

### Search Not Working
- Install search plugins in qBittorrent's Search Engine
- Verify plugins are enabled
- Some plugins may require updating

### Authentication Failed
- Check your username and password in `.env`
- Default credentials are usually `admin`/`adminadmin`
- You can change these in qBittorrent's Web UI settings

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
