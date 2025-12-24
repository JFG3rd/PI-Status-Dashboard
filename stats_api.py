#!/usr/bin/env python3
"""
Modular Pi5 NVR Dashboard API with Hardware Auto-Detection
Supports various hardware configurations (SD-only, NVMe, Hailo, USB SSD, etc.)
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import subprocess
import psutil
import os
import time
import ssl
import base64
from datetime import timedelta

# PAM authentication
try:
    import pam
    PAM_AVAILABLE = True
except ImportError:
    PAM_AVAILABLE = False
    print("WARNING: python-pam not available, authentication disabled")

# Cache for stats (refresh every 5 seconds)
STATS_CACHE = {}
CACHE_DURATION = 5

# Hardware detection cache
HARDWARE_CACHE = None
HARDWARE_CACHE_TIME = 0
HARDWARE_CACHE_DURATION = 30  # Re-detect every 30 seconds

# Import Scrypted stats module
try:
    from scrypted_stats import get_all_scrypted_stats
    SCRYPTED_AVAILABLE = True
except ImportError:
    SCRYPTED_AVAILABLE = False
    def get_all_scrypted_stats():
        return {'error': 'Module not available'}


def detect_hardware():
    """Detect available hardware components"""
    global HARDWARE_CACHE, HARDWARE_CACHE_TIME
    
    current_time = time.time()
    if HARDWARE_CACHE and (current_time - HARDWARE_CACHE_TIME) < HARDWARE_CACHE_DURATION:
        return HARDWARE_CACHE
    
    hardware = {
        'nvme': False,
        'usb_ssd': False,
        'sd_card': False,
        'hailo': False,
        'docker': False,
        'scrypted': False,
        'boot_device': 'unknown'
    }
    
    # Detect NVMe
    try:
        if any(os.path.exists(f'/dev/nvme{i}') or os.path.exists(f'/host/dev/nvme{i}') 
               for i in range(5)):
            hardware['nvme'] = True
    except:
        pass
    
    # Detect USB SSD (backup drive)
    try:
        if os.path.exists('/mnt/backup-ssd') and os.path.ismount('/mnt/backup-ssd'):
            hardware['usb_ssd'] = True
    except:
        pass
    
    # Detect SD card
    try:
        # Check multiple possible locations
        sd_paths = ['/dev/mmcblk0', '/host/dev/mmcblk0', '/dev/mmcblk0p1', '/host/dev/mmcblk0p1']
        if any(os.path.exists(path) for path in sd_paths):
            hardware['sd_card'] = True
    except:
        pass
    
    # Detect boot device
    try:
        with open('/proc/cmdline', 'r') as f:
            cmdline = f.read()
            if 'root=/dev/nvme' in cmdline or 'root=PARTUUID=' in cmdline:
                # Check if PARTUUID points to NVMe
                hardware['boot_device'] = 'nvme' if hardware['nvme'] else 'unknown'
            elif 'root=/dev/mmcblk0' in cmdline:
                hardware['boot_device'] = 'sd'
            else:
                hardware['boot_device'] = 'nvme' if hardware['nvme'] else 'sd'
    except:
        hardware['boot_device'] = 'nvme' if hardware['nvme'] else 'sd'
    
    # Detect Hailo
    try:
        if os.path.exists('/dev/hailo0') or os.path.exists('/host/dev/hailo0'):
            hardware['hailo'] = True
    except:
        pass
    
    # Detect Docker
    try:
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, timeout=2)
        if result.returncode == 0:
            hardware['docker'] = True
    except:
        pass
    
    # Detect Scrypted (if Docker available)
    if hardware['docker']:
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', 'name=scrypted', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=2
            )
            if 'scrypted' in result.stdout:
                hardware['scrypted'] = True
        except:
            pass
    
    HARDWARE_CACHE = hardware
    HARDWARE_CACHE_TIME = current_time
    return hardware


class StatsHandler(BaseHTTPRequestHandler):
    def check_auth(self):
        """Check HTTP Basic Authentication using PAM"""
        if not PAM_AVAILABLE:
            print("PAM not available - allowing access")
            return True
        
        auth_header = self.headers.get('Authorization')
        if not auth_header:
            print("No Authorization header provided")
            return False
        
        try:
            auth_type, credentials = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                print(f"Wrong auth type: {auth_type}")
                return False
            
            decoded = base64.b64decode(credentials).decode('utf-8')
            username, password = decoded.split(':', 1)
            
            print(f"Attempting PAM authentication for user: {username}")
            p = pam.pam()
            result = p.authenticate(username, password)
            
            if result:
                print(f"✓ Authentication successful for user: {username}")
            else:
                print(f"✗ Authentication failed for user: {username}")
            
            return result
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def require_auth(self):
        """Send 401 Unauthorized response"""
        self.send_response(401)
        self.send_header('WWW-Authenticate', 'Basic realm="Pi5 NVR Dashboard"')
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>401 Unauthorized</h1></body></html>')
    
    def do_GET(self):
        # Allow favicon without authentication
        if self.path in ['/favicon.svg', '/favicon.ico']:
            self.send_response(200)
            self.send_header('Content-Type', 'image/svg+xml')
            self.send_header('Cache-Control', 'public, max-age=3600')
            self.end_headers()
            
            favicon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
                <defs>
                    <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#2196F3"/>
                        <stop offset="100%" style="stop-color:#1976D2"/>
                    </linearGradient>
                </defs>
                <circle cx="50" cy="50" r="48" fill="url(#g)"/>
                <text x="50" y="73" font-family="Georgia,serif" font-size="70" font-weight="bold" fill="white" text-anchor="middle">π</text>
            </svg>'''
            self.wfile.write(favicon_svg.encode())
            return
        
        # Check authentication for all other requests
        if not self.check_auth():
            self.require_auth()
            return
        
        if self.path == '/api/hardware':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            hardware = detect_hardware()
            self.wfile.write(json.dumps(hardware).encode())
            
        elif self.path == '/api/backup/status':
            self.proxy_to_backup_api('/api/backup/status')
            
        elif self.path == '/api/backup/log':
            self.proxy_to_backup_api('/api/backup/log')
        
        elif self.path == '/api/backup/list':
            self.proxy_to_backup_api('/api/backup/list')
        
        elif self.path == '/api/backup/stats':
            self.proxy_to_backup_api('/api/backup/stats')
            
        elif self.path == '/api/stats':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            stats = self.get_system_stats()
            self.wfile.write(json.dumps(stats).encode())
            
        elif self.path.startswith('/api/container/logs'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)
            container = query.get('container', [''])[0]
            
            result = self.get_container_logs(container)
            self.wfile.write(json.dumps(result).encode())
            
        elif self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.end_headers()
            
            with open('/app/index.html', 'r') as f:
                self.wfile.write(f.read().encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def proxy_to_backup_api(self, path):
        """Proxy request to backup API"""
        try:
            import urllib.request
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            auth_header = self.headers.get('Authorization', '')
            req = urllib.request.Request(
                f'https://172.17.0.1:8081{path}',
                headers={'Authorization': auth_header}
            )
            
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                data = response.read()
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_POST(self):
        if not self.check_auth():
            self.require_auth()
            return
        
        content_length = self.headers.get('Content-Length')
        body = self.rfile.read(int(content_length)).decode() if content_length else ''
            
        if self.path == '/api/backup':
            self.proxy_post_to_backup_api('/api/backup', body)
            
        elif self.path == '/api/restore':
            self.proxy_post_to_backup_api('/api/restore', body)
            
        elif self.path == '/api/backup/delete':
            self.proxy_post_to_backup_api('/api/backup/delete', body)
        
        elif self.path == '/api/restart':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            result = self.restart_system()
            self.wfile.write(json.dumps(result).encode())
            
        elif self.path in ['/api/container/restart', '/api/container/stop', '/api/container/start']:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            data = json.loads(body) if body else {}
            container = data.get('container', '')
            action = self.path.split('/')[-1]
            
            result = self.control_container(container, action)
            self.wfile.write(json.dumps(result).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
    
    def proxy_post_to_backup_api(self, path, body):
        """Proxy POST request to backup API"""
        try:
            import urllib.request
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            auth_header = self.headers.get('Authorization', '')
            req = urllib.request.Request(
                f'https://172.17.0.1:8081{path}',
                data=body.encode() if body else None,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': auth_header
                }
            )
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                data = response.read()
                
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def get_backup_stats(self):
        """Get backup statistics from backup API"""
        try:
            import urllib.request
            from datetime import datetime
            
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            auth_header = self.headers.get('Authorization', '')
            req = urllib.request.Request(
                'https://172.17.0.1:8081/api/backup/list',
                headers={'Authorization': auth_header}
            )
            
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                data = json.loads(response.read().decode())
            
            if 'backups' in data:
                backups = data['backups']
                total_count = len(backups)
                
                # Find most recent backup by parsing filenames
                last_backup = None
                if backups:
                    # Sort by timestamp in filename
                    sorted_backups = sorted(backups, key=lambda b: b.get('timestamp', ''), reverse=True)
                    if sorted_backups:
                        last_backup = sorted_backups[0].get('timestamp', 'Unknown')
                
                # Calculate total size
                total_size = sum(b.get('size', 0) for b in backups)
                
                return {
                    'total_count': total_count,
                    'last_backup': last_backup,
                    'total_size_bytes': total_size,
                    'total_size': f"{total_size / (1024**3):.2f} GB" if total_size > 0 else "0 GB"
                }
            else:
                return {'total_count': 0, 'last_backup': None, 'total_size': '0 GB'}
        except Exception as e:
            return {'error': str(e), 'total_count': 0}
    
    def restart_system(self):
        """Restart the system"""
        try:
            subprocess.Popen(['sudo', 'shutdown', '-r', '+0.5'])
            return {'success': True, 'message': 'System restart initiated'}
        except Exception as e:
            return {'success': False, 'message': str(e)}

    def control_container(self, container_name, action):
        """Control a Docker container"""
        try:
            result = subprocess.run(
                ['docker', action, container_name],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                return {'success': True, 'message': f'Container {action}ed successfully'}
            else:
                return {'success': False, 'message': result.stderr or 'Command failed'}
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_container_logs(self, container_name):
        """Get container logs"""
        try:
            result = subprocess.run(
                ['docker', 'logs', '--tail', '500', container_name],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0:
                return {'success': True, 'logs': result.stdout + result.stderr}
            else:
                return {'success': False, 'message': result.stderr, 'logs': ''}
        except Exception as e:
            return {'success': False, 'message': str(e), 'logs': ''}

    def get_system_stats(self):
        """Gather all system statistics with caching"""
        global STATS_CACHE
        current_time = time.time()
        
        if 'timestamp' in STATS_CACHE and (current_time - STATS_CACHE['timestamp']) < CACHE_DURATION:
            return STATS_CACHE['data']
        
        hardware = detect_hardware()
        
        stats = {
            'hardware': hardware,
            'cpu': self.get_cpu_stats(),
            'memory': self.get_memory_stats(),
            'disk': self.get_disk_stats(hardware),
            'network': self.get_network_stats(),
            'system': self.get_system_info()
        }
        
        if hardware['docker']:
            stats['docker'] = self.get_docker_stats()
        
        if hardware['hailo']:
            stats['hailo'] = self.get_hailo_stats()
        
        if hardware['scrypted'] and SCRYPTED_AVAILABLE:
            stats['scrypted'] = get_all_scrypted_stats()
        
        STATS_CACHE = {'timestamp': current_time, 'data': stats}
        return stats
    
    def get_cpu_stats(self):
        """Get CPU stats"""
        try:
            with open('/host/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
        except:
            temp = 0.0
        
        cpu_percent = psutil.cpu_percent(interval=None)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        if cpu_percent == 0.0:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        
        load_avg = os.getloadavg()
        
        return {
            'temperature': f"{temp:.1f}",
            'usage': cpu_percent,
            'per_core': per_core,
            'load_avg': f"{load_avg[0]:.2f} {load_avg[1]:.2f} {load_avg[2]:.2f}"
        }
    
    def get_memory_stats(self):
        """Get memory stats"""
        mem = psutil.virtual_memory()
        return {
            'total': f"{mem.total / (1024**3):.1f} GB",
            'used': f"{mem.used / (1024**3):.1f} GB",
            'available': f"{mem.available / (1024**3):.1f} GB",
            'percent': mem.percent
        }
    
    def get_disk_stats(self, hardware):
        """Get disk stats based on available hardware"""
        result = {}
        
        # Boot device stats
        boot_device = hardware['boot_device']
        root_usage = psutil.disk_usage('/')
        
        if boot_device == 'nvme' and hardware['nvme']:
            result['nvme'] = {
                'total': f"{root_usage.total / (1024**3):.1f} GB",
                'used': f"{root_usage.used / (1024**3):.1f} GB",
                'available': f"{root_usage.free / (1024**3):.1f} GB",
                'percent': root_usage.percent,
                'boot': True
            }
        elif boot_device == 'sd' and hardware['sd_card']:
            result['sd_card'] = {
                'total': f"{root_usage.total / (1024**3):.1f} GB",
                'used': f"{root_usage.used / (1024**3):.1f} GB",
                'available': f"{root_usage.free / (1024**3):.1f} GB",
                'percent': root_usage.percent,
                'boot': True
            }
        
        # USB SSD backup drive
        if hardware['usb_ssd']:
            try:
                usb_usage = psutil.disk_usage('/mnt/backup-ssd')
                result['usb_ssd'] = {
                    'total': f"{usb_usage.total / (1024**3):.1f} GB",
                    'used': f"{usb_usage.used / (1024**3):.1f} GB",
                    'available': f"{usb_usage.free / (1024**3):.1f} GB",
                    'percent': usb_usage.percent,
                    'mounted': True
                }
            except:
                result['usb_ssd'] = {'mounted': False}
        
        # SD card (if not boot device but present)
        if hardware['sd_card'] and boot_device != 'sd':
            # Find SD card partitions and get total size
            try:
                import subprocess
                # Try different device paths
                device_path = None
                for path in ['/dev/mmcblk0', '/host/dev/mmcblk0']:
                    if os.path.exists(path):
                        device_path = path
                        break
                
                if not device_path:
                    result['sd_card'] = {'present': True, 'accessible': False}
                else:
                    # Get full SD card size and partition info
                    lsblk_result = subprocess.run(
                        ['lsblk', '-b', '-o', 'NAME,SIZE,MOUNTPOINT', device_path],
                        capture_output=True, text=True, timeout=5
                    )
                    
                    if lsblk_result.returncode == 0:
                        lines = lsblk_result.stdout.strip().split('\n')
                        total_size = 0
                        used_size = 0
                        
                        # Parse lsblk output (skip header line)
                        for i, line in enumerate(lines[1:], 1):
                            # Clean up tree characters (├─, └─, etc.)
                            clean_line = line.replace('├─', '').replace('└─', '').replace('│ ', '')
                            parts = clean_line.split()
                            
                            if len(parts) >= 2:
                                # First data line is the main device - get total size
                                if i == 1:
                                    try:
                                        total_size = int(parts[1])
                                    except (ValueError, IndexError):
                                        pass
                                
                                # Check if partition has a mountpoint
                                if len(parts) >= 3:
                                    mount = parts[2]
                                    try:
                                        usage = psutil.disk_usage(mount)
                                        used_size += usage.used
                                    except:
                                        pass
                        
                        if total_size > 0:
                            available_size = total_size - used_size
                            percent = (used_size / total_size) * 100 if total_size > 0 else 0
                            
                            result['sd_card'] = {
                                'total': f"{total_size / (1024**3):.1f} GB",
                                'used': f"{used_size / (1024**3):.1f} GB",
                                'available': f"{available_size / (1024**3):.1f} GB",
                                'percent': round(percent, 1),
                                'boot': False
                            }
                        else:
                            result['sd_card'] = {'present': True, 'mounted': False}
                    else:
                        result['sd_card'] = {'present': True, 'mounted': False, 'error': lsblk_result.stderr}
            except Exception as e:
                result['sd_card'] = {'present': True, 'error': str(e)}
        
        return result
    
    def get_network_stats(self):
        """Get network stats"""
        ip = "192.168.178.31"
        
        rx_bytes = 0
        tx_bytes = 0
        try:
            for iface in ['eth0', 'wlan0', 'end0']:
                try:
                    with open(f'/host/sys/class/net/{iface}/statistics/rx_bytes', 'r') as f:
                        rx_bytes += int(f.read().strip())
                    with open(f'/host/sys/class/net/{iface}/statistics/tx_bytes', 'r') as f:
                        tx_bytes += int(f.read().strip())
                except:
                    pass
        except:
            net_io = psutil.net_io_counters()
            rx_bytes = net_io.bytes_recv
            tx_bytes = net_io.bytes_sent
        
        return {
            'ip': ip,
            'rx': f"{rx_bytes / (1024**3):.2f} GB",
            'tx': f"{tx_bytes / (1024**3):.2f} GB"
        }

    def get_docker_stats(self):
        """Get Docker stats"""
        try:
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 
                 '{{.Name}}|{{.CPUPerc}}|{{.MemUsage}}|{{.MemPerc}}|{{.NetIO}}|{{.BlockIO}}'],
                capture_output=True, text=True, timeout=4
            )
            
            if not result.stdout:
                return {'containers': []}
            
            containers = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 4:
                    containers.append({
                        'name': parts[0],
                        'cpu': parts[1],
                        'memory': parts[2],
                        'mem_percent': parts[3],
                        'network': parts[4] if len(parts) > 4 else 'N/A',
                        'disk': parts[5] if len(parts) > 5 else 'N/A',
                        'status': 'running'
                    })
            
            return {'containers': containers}
            
        except Exception as e:
            return {'containers': [], 'error': str(e)}

    def get_hailo_stats(self):
        """Get Hailo stats"""
        stats = {
            'device': 'Not found',
            'driver': 'Not loaded',
            'driver_version': 'N/A',
            'pci_address': 'N/A',
            'status': '❌ Inactive'
        }
        
        try:
            for path in ['/host/dev/hailo0', '/dev/hailo0']:
                if os.path.exists(path):
                    stats['device'] = '/dev/hailo0'
                    break
            
            try:
                with open('/host/proc/modules', 'r') as f:
                    for line in f:
                        if 'hailo_pci' in line:
                            parts = line.split()
                            stats['driver'] = 'hailo_pci'
                            stats['driver_version'] = parts[1] if len(parts) > 1 else 'Loaded'
                            break
            except:
                pass
            
            if os.path.exists('/host/sys/bus/pci/devices'):
                for pci_dev in os.listdir('/host/sys/bus/pci/devices'):
                    vendor_path = f'/host/sys/bus/pci/devices/{pci_dev}/vendor'
                    if os.path.exists(vendor_path):
                        with open(vendor_path, 'r') as f:
                            vendor = f.read().strip()
                        if vendor == '0x1e60':
                            stats['pci_address'] = pci_dev
                            break
            
            if stats['device'] != 'Not found' and stats['driver'] != 'Not loaded':
                stats['status'] = '✅ Active'
            
            return stats
            
        except Exception as e:
            stats['status'] = f'Error: {str(e)}'
            return stats
    
    def get_system_info(self):
        """Get system info"""
        uptime_seconds = int(psutil.boot_time())
        uptime = str(timedelta(seconds=int(time.time() - uptime_seconds)))
        
        return {'uptime': uptime}
    
    def log_message(self, format, *args):
        """Suppress HTTP request logging"""
        pass

def run_server(port=8443):
    """Start the HTTPS server"""
    server_address = ('', port)
    httpd = HTTPServer(server_address, StatsHandler)
    
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(
            certfile='/etc/ssl/dashboard/server.crt',
            keyfile='/etc/ssl/dashboard/server.key'
        )
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        print(f"✓ HTTPS dashboard server running on port {port}")
        print(f"✓ Access at: https://192.168.178.31:{port}")
        print(f"✓ Authentication: Enabled (PAM)")
    except Exception as e:
        print(f"WARNING: SSL failed, falling back to HTTP: {e}")
        print(f"HTTP dashboard server running on port {port}")
    
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
