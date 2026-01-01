docker-compose up -d
# Pi Status Dashboard (Pi 4/5)

Raspberry Pi dashboard for local NVR/edge setups. It autodetects available hardware (NVMe, SD, USB SSD, Hailo AI, Docker, Scrypted), shows live status, and controls backup/restore with abort support. HTTPS + PAM auth.

## What it shows
- CPU temp/usage per core, load averages, uptime; memory usage; network RX/TX, host IP/gateway/subnet/DHCP flag.
- Storage: boot device (NVMe or SD), SD card stats, USB SSD presence, and usage bars.
- Docker: running containers with CPU/mem, start/stop/restart/logs controls.
- Hailo AI: PCI device, driver/version, power state when /dev/hailo0 exists.
- Scrypted: container status/uptime plus camera/event/storage summaries.
- Backup/Restore: launch backups/restores, view logs (error lines red), and now abort running backups.

## Architecture
- Backend: `stats_api.py` (Python 3.11) serves HTTPS on 8443 inside the container; uses psutil, Docker CLI, and nsenter to gather stats; proxies backup calls to the host backup API on 8081.
- Backup API: `backup-api-server.py` on the host (HTTPS, PAM). It launches `backup-restore-service.sh` and now tracks the process for abort requests.
- Backup engine: `backup-restore-service.sh` (bash) with NVMe/USB/network targets, component selection, manifest, and `pipefail`+fatal exits.
- Frontend: `index.html` (vanilla HTML/CSS/JS) with a modal for Backup/Restore, abort button, and colored log output.

## Backup behavior
- Targets: NVMe (`nvme`), USB SSD (`usb`), or network staging (`network`). The UI defaults to NVMe; the API defaults to NVMe when no target is given.
- Paths (env-configurable):
  - `NVME_BACKUP_PATH` (default `/nvme-backups`)
  - `USB_BACKUP_PATH` (default `/mnt/backup-ssd/backups`)
  - `BACKUP_DEFAULT_PATH` mirrors `NVME_BACKUP_PATH` in the dashboard display.
- Abort: the dashboard abort button calls `/api/backup/abort`, which kills the running backup process group and marks status/logs as aborted.
- Errors: fatal rsync failures abort the backup; log lines containing `ERROR/Failed` render red in the UI.

## Environment (.env)
- `DASHBOARD_IP_OVERRIDE` — force the host IP if auto-detect is wrong.
- `NETWORK_INTERFACE_PRIORITY` — comma list for IP detection preference.
- `NVME_BACKUP_PATH`, `USB_BACKUP_PATH`, `BACKUP_DEFAULT_PATH` — backup destinations; defaults favor NVMe.
- `TZ` — timezone.

## Deploy (compose)
```bash
cd /home/jessegreene/status-dashboard
docker-compose up -d --build
```
- HTTPS on host 8443. Expects `/etc/ssl/dashboard/server.crt` and `server.key`.
- Key mounts: docker.sock (ro), /sys,/proc (ro), /dev,/boot/firmware, /home/jessegreene, /mnt/backup-ssd, /scrypted/nvr (ro), /etc/shadow,/etc/passwd (ro for PAM).

## Quick commands
- Logs: `docker logs -f pi5-status-dashboard`
- Rebuild: `docker-compose build --no-cache && docker-compose up -d`
- Stop: `docker-compose down`

## Notes
- Stats cache: 5s; hardware cache: 30s.
- Backup API is expected at `https://172.17.0.1:8081` from inside the dashboard container.
- If host IP is still wrong, set `DASHBOARD_IP_OVERRIDE` in `.env`.

## Screenshots
- Main dashboard: [docs/screenshots/PIStatus-MainPage.png](docs/screenshots/PIStatus-MainPage.png)
- Backup Manager: [docs/screenshots/PIStatus-BackupPage.png](docs/screenshots/PIStatus-BackupPage.png)
- Restore Manager: [docs/screenshots/PIStatus-RestorePage.png](docs/screenshots/PIStatus-RestorePage.png)
