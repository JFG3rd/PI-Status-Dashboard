# Pi Status Dashboard (Pi 4/5)

Raspberry Pi dashboard for local NVR/edge setups. It autodetects available hardware (NVMe, SD, USB SSD, Hailo AI, Docker, Scrypted) and presents live status, backup/restore controls, and container actions over HTTPS with PAM authentication.

## Features
- System cards: CPU temp/usage per core, load averages, uptime, memory usage, network RX/TX and IP.
- Storage-aware: detects boot device (NVMe or SD), shows additional SD/USB SSD volumes with usage and availability.
- Backup & Restore: proxied calls to the companion backup API (backup-api-server.py) for listing backups, launching backups/restores, and viewing logs.
- Docker awareness: lists running containers, live CPU/memory stats, and start/stop/restart controls.
- Hailo AI card: shows PCI device, driver, version, power state when /dev/hailo0 is present.
- Scrypted card: container status/uptime plus basic camera, event, and storage stats pulled from /scrypted/nvr.
- Responsive UI: updates every ~3s; cards hide automatically if the related hardware/software is absent.

## Architecture
- Backend: `stats_api.py` (Python 3.11) runs an HTTPS server on port 8443 inside the container. It gathers stats via psutil, shell helpers, and Docker CLI; proxies backup calls to https://172.17.0.1:8081.
- Frontend: `index.html` (vanilla HTML/CSS/JS) renders cards and modals for backup/restore and container control.
- Optional Scrypted helpers: `scrypted_stats.py` and `scrypted_update.js` provide lightweight stats for the Scrypted NVR container and recording folders.

## API Endpoints
- `/api/stats` — aggregated system stats (hardware flags, cpu, memory, disk, network, docker, hailo, scrypted).
- `/api/hardware` — hardware detection flags and boot device.
- `/api/backup`, `/api/restore`, `/api/backup/delete`, `/api/backup/status`, `/api/backup/log`, `/api/backup/list`, `/api/backup/stats` — proxied to the backup API.
- `/api/container/{start|stop|restart}` and `/api/container/logs?container=<name>` — container control/log retrieval.

## Deployment (Docker Compose)
```bash
cd /home/jessegreene/status-dashboard
docker-compose build
docker-compose up -d
```
- Serves HTTPS on host port 8443 (container 8443). Certificates expected at `/etc/ssl/dashboard/server.crt` and `server.key`.
- Volumes (from docker-compose.yml):
  - `/var/run/docker.sock` read-only for container stats
  - `/sys` and `/proc` read-only for temperature, CPU, network counters
  - `/dev` and `/boot/firmware` for SD/NVMe detection
  - `/mnt/backup-ssd` and `/home/jessegreene` for backup UI integration
  - `/scrypted/nvr` read-only for NVR stats
  - `/etc/shadow`, `/etc/passwd` read-only for PAM auth

### Environment configuration (.env)
The compose file now loads a `.env` (see the sample checked in). Key variables:
- `DASHBOARD_IP_OVERRIDE` — only use if auto-detect is wrong; forces the Host IP shown.
- `NETWORK_INTERFACE_PRIORITY` — comma list for IP auto-detect preference (default `eth0,end0,wlan0`).
- `BACKUP_DEFAULT_PATH` — path shown in the Backup card (default `/mnt/backup-ssd/backups`).
- `TZ` — timezone (default `Europe/Berlin`).

IP detection notes: the dashboard now tries (in order) `DASHBOARD_IP_OVERRIDE`, host default route (nsenter + ip route/addr) to get IP/gateway/subnet and DHCP flag, then proc/nsenter fallbacks, then container IP. If it still shows 0.0.0.0, set `DASHBOARD_IP_OVERRIDE` in `.env` to the LAN IP.

## Quick Run Commands
- One-liner deploy: `cd /home/jessegreene/status-dashboard && docker-compose up -d --build`
- Logs: `docker logs -f pi5-status-dashboard`
- Rebuild without cache: `docker-compose build --no-cache && docker-compose up -d`
- Stop/remove: `docker-compose down`

## Backup API Dependency
- The dashboard proxies backup/restore calls to the companion backup API at `https://172.17.0.1:8081` (inside the Docker network).
- That API is provided by `backup-api-server.py` (runs on the host or another container). Ensure it is running and reachable from the dashboard container.
- Expected TLS certs for the backup API are already trusted in the dashboard (TLS verification is skipped in the proxy). If you change host/port, update the proxy URLs in `stats_api.py`.

## Authentication
- HTTP Basic backed by system PAM. Use a local user that exists on the host. If PAM is unavailable, auth is bypassed (logged to stdout).

## Configuration Notes
- `stats_api.py` caches stats for 5s and hardware detection for 30s.
- Network IP is currently hardcoded in `get_network_stats()`; adjust if your host IP changes.
- Backup API is expected at `https://172.17.0.1:8081` inside the Docker network.

## Local Development
- Run directly: `python3 stats_api.py` (expects certs at /etc/ssl/dashboard). For quick HTTP testing, remove or adjust TLS loading near `run_server()`.
- Frontend lives in `index.html`; main JS update loop is near the bottom (updateStats). UI uses only inline CSS/JS.

## Hardware Detection Behavior
- NVMe: detected via /dev/nvme*; marked as boot if root is on NVMe.
- SD: detected via /dev/mmcblk0*; marked as boot when root is on SD, otherwise shown as secondary with lsblk/psutil stats.
- USB SSD: shown when /mnt/backup-ssd is mounted.
- Hailo: shown when /dev/hailo0 and hailo_pci module exist.
- Docker: gated on docker CLI availability; Scrypted card appears only when the `scrypted` container is running.

## Screenshots
Main dashboard
![Pi Status Dashboard main page](docs/screenshots/PIStatus-MainPage.png)

Backup Manager modal
![Backup Manager](docs/screenshots/PIStatus-BackupPage.png)

Restore Manager modal
![Restore Manager](docs/screenshots/PIStatus-RestorePage.png)
