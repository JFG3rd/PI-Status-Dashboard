# Pi5 Dashboard Improvements

**Date:** December 17, 2025  
**Author:** GitHub Copilot  

## Issues Fixed

### 1. SD Card Not Displaying in Storage Card ✅

**Problem:** The dashboard hardcoded NVMe storage display and didn't show SD card information.

**Root Cause:**
- JavaScript in `index.html` (line 853) only referenced `data.disk.nvme`
- No logic to detect and display SD card as boot device or secondary storage
- The backend API correctly detected SD cards, but frontend ignored the data

**Solution:**
- Added dynamic boot device detection that checks both `data.disk.nvme` and `data.disk.sd_card`
- Updates the storage section header dynamically based on boot device (NVMe or SD Card)
- Added a new "SD Card" section that displays when SD card is present but not the boot device
- Enhanced SD card detection in backend to check multiple device paths

**Files Modified:**
- `index.html` - Lines 853-867 (storage display logic)
- `index.html` - Lines 669-675 (added SD card HTML section)
- `stats_api.py` - Lines 77-81 (improved SD card detection)
- `stats_api.py` - Lines 555-580 (enhanced SD card stats collection)

---

### 2. Backup List Not Showing in Restore Manager ✅

**Problem:** The Restore Manager modal showed "No backups found" even when backups existed.

**Root Cause:**
- API returns `{"backups": [...]}` format
- Frontend expected raw array and assigned `allBackups = data` instead of `allBackups = data.backups`
- This caused `allBackups` to be an empty object, not an array

**Solution:**
- Fixed backup list loading to properly extract the `backups` array from API response
- Added fallback logic: `allBackups = data.backups || data || []`
- Added console logging for debugging backup loading
- Enhanced error messages with more detail
- Improved backend API to handle both array and object responses from backup script

**Files Modified:**
- `index.html` - Lines 1191-1201 (backup list loading)
- `backup-api-server.py` - Lines 189-198 (API response normalization)

---

### 3. Hardware Auto-Detection Flexibility ✅

**Problem:** Dashboard always showed Docker, Hailo, and Scrypted cards even when not installed.

**Solution:**
- Made Docker, Hailo, and Scrypted cards hidden by default
- Added hardware detection logic that shows/hides cards based on `data.hardware` flags
- Cards now only appear when the corresponding hardware/software is detected
- Makes dashboard reusable for different Pi5 configurations

**Implementation:**
```javascript
// Hardware auto-detection - show/hide cards based on available hardware
if (data.hardware) {
    dockerCard.style.display = data.hardware.docker ? 'block' : 'none';
    hailoCard.style.display = data.hardware.hailo ? 'block' : 'none';
    scryptedCard.style.display = data.hardware.scrypted ? 'block' : 'none';
}
```

**Files Modified:**
- `index.html` - Lines 722, 762, 719 (added `style="display: none;"` to cards)
- `index.html` - Lines 811-829 (hardware detection visibility logic)

---

## Architecture Overview

### Backend (`stats_api.py`)
```
┌─────────────────────────────────────────────────┐
│         Hardware Detection Layer                │
│  - detect_hardware() function                   │
│  - Caches results for 30 seconds                │
│  - Detects: NVMe, SD Card, USB SSD, Hailo,     │
│    Docker, Scrypted, Boot Device                │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│         Stats Collection Layer                   │
│  - get_disk_stats() - Dynamic storage stats     │
│  - get_cpu_stats() - CPU temp & usage           │
│  - get_memory_stats() - RAM usage               │
│  - get_docker_stats() - Container info          │
│  - get_hailo_stats() - AI accelerator           │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│           API Endpoints                          │
│  /api/stats - All system statistics             │
│  /api/hardware - Hardware detection results     │
│  /api/backup/list - Available backups           │
└─────────────────────────────────────────────────┘
```

### Frontend (`index.html`)
```
┌─────────────────────────────────────────────────┐
│         Periodic Data Fetching                   │
│  - updateStats() every 3 seconds                │
│  - Fetches /api/stats                           │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│     Hardware-Based Card Visibility               │
│  - Show/hide Docker card                        │
│  - Show/hide Hailo card                         │
│  - Show/hide Scrypted card                      │
│  - Dynamically adjust storage display           │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│          Dynamic UI Updates                      │
│  - Update storage section based on boot device  │
│  - Display SD card as primary or secondary      │
│  - Show relevant cards only                     │
└─────────────────────────────────────────────────┘
```

---

## Usage for Future Pi5 Projects

### Automatic Hardware Detection

The dashboard now automatically detects and displays:

1. **Storage Devices**
   - NVMe SSD (as boot or secondary)
   - SD Card (as boot or secondary)
   - USB SSD (backup drive)

2. **AI Hardware**
   - Hailo AI accelerator (only shown if detected)

3. **Software Platforms**
   - Docker containers (only shown if Docker installed)
   - Scrypted NVR (only shown if Scrypted container running)

### Adding New Hardware Support

To add support for new hardware (e.g., Coral TPU, additional storage):

1. **Backend Detection** (`stats_api.py`):
```python
def detect_hardware():
    hardware = {
        # Existing hardware...
        'coral_tpu': False,  # Add new hardware flag
    }
    
    # Detect Coral TPU
    try:
        if os.path.exists('/dev/apex_0'):
            hardware['coral_tpu'] = True
    except:
        pass
    
    return hardware
```

2. **Add Stats Collection** (`stats_api.py`):
```python
def get_coral_stats(self):
    """Get Coral TPU statistics"""
    stats = {
        'device': 'Not found',
        'status': '❌ Inactive'
    }
    # Your detection logic here
    return stats
```

3. **Add to Main Stats** (`stats_api.py`):
```python
if hardware['coral_tpu']:
    stats['coral'] = self.get_coral_stats()
```

4. **Frontend Display** (`index.html`):
```html
<!-- Coral TPU Card -->
<div class="card" id="coralCard" style="display: none;">
    <h2>🧠 Coral TPU</h2>
    <!-- Your stats display here -->
</div>
```

5. **Add Visibility Logic** (`index.html`):
```javascript
if (data.hardware) {
    const coralCard = document.getElementById('coralCard');
    if (coralCard) {
        coralCard.style.display = data.hardware.coral_tpu ? 'block' : 'none';
    }
}
```

---

## Testing Recommendations

### 1. SD Card Display
- Boot from NVMe with SD card inserted → Should show NVMe as primary, SD as secondary
- Boot from SD card → Should show SD Card as primary storage
- No SD card → Should only show NVMe storage

### 2. Backup/Restore
- Create a backup → Should appear in list immediately after refresh
- Multiple backups → Should display all with correct sorting
- No backups → Should show "No backups found" message

### 3. Hardware Auto-Detection
- Remove Hailo → Card should disappear
- Stop Docker → Docker card should disappear
- Stop Scrypted container → Scrypted card should disappear

---

## Configuration Variables

### Backend Configuration (`stats_api.py`)
```python
STATS_CACHE_DURATION = 5        # Stats cache timeout (seconds)
HARDWARE_CACHE_DURATION = 30    # Hardware detection cache (seconds)
```

### Frontend Configuration (`index.html`)
```javascript
// Update interval (line 1700+)
setInterval(updateStats, 3000);  // Update every 3 seconds
```

---

## Deployment

### Rebuild Docker Container
```bash
cd /home/jessegreene/status-dashboard
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Check Logs
```bash
docker logs -f pi5-status-dashboard
```

### Verify Backup API
```bash
curl -k https://192.168.178.31:8081/api/backup/list
```

---

## Known Limitations

1. **SD Card Detection in Docker**
   - Requires `/host/dev` volume mount to detect SD card from within container
   - Update `docker-compose.yml` if detection fails:
     ```yaml
     volumes:
       - /dev:/host/dev:ro
     ```

2. **Backup Script Path**
   - Hardcoded in `backup-api-server.py` as `/home/jessegreene/backup-restore-service.sh`
   - Update if script location changes

3. **Network IP**
   - Hardcoded in `stats_api.py` line 617: `ip = "192.168.178.31"`
   - Consider making this dynamic by detecting actual interface IP

---

## Future Enhancements

1. **Plugin System**
   - Create modular plugin architecture for easy hardware additions
   - JSON configuration file for enabling/disabling features

2. **Responsive Design**
   - Improve mobile/tablet layouts
   - Collapsible card sections

3. **Historical Data**
   - Store and graph historical CPU/memory/disk usage
   - Backup history timeline

4. **Notifications**
   - Email/webhook alerts for high temperature, disk full, etc.
   - Backup completion notifications

5. **Multi-Device Support**
   - Dashboard that monitors multiple Pi5 devices
   - Centralized management interface

---

## Troubleshooting

### SD Card Not Showing
1. Check device exists: `ls -la /dev/mmcblk*`
2. Verify Docker volume mount: `docker inspect pi5-status-dashboard`
3. Check API response: View browser console for `data.disk` object
4. Review backend logs: `docker logs pi5-status-dashboard`

### Backup List Empty
1. Verify backup script works: `./backup-restore-service.sh list`
2. Check API server: `sudo systemctl status backup-api`
3. Test API endpoint: `curl -k https://localhost:8081/api/backup/list`
4. Check browser console for JavaScript errors

### Cards Not Auto-Hiding
1. Verify hardware detection: Navigate to `https://your-pi:8443/api/hardware`
2. Check browser console for `data.hardware` object
3. Ensure cards have correct IDs: `dockerCard`, `hailoCard`, `scryptedCard`

---

## Contact

For issues or questions about this dashboard:
- **Original Author:** Jesse Greene (JFG3rd@gmail.com)
- **Location:** Berlin, Germany
- **Updates By:** GitHub Copilot (December 2025)
