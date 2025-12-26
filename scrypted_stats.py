#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime

CAMERA_NAMES = {'46': 'IPC-F22', '27': 'IPC-G22'}

def get_scrypted_cameras():
    cameras = []
    recordings_base = '/scrypted/nvr/recordings'
    try:
        for item in os.listdir(recordings_base):
            if item.startswith('scrypted-'):
                camera_id = item.replace('scrypted-', '')
                camera_path = os.path.join(recordings_base, item)
                camera_name = CAMERA_NAMES.get(camera_id, f'Camera {camera_id}')
                
                # Check if recording by looking for recent files
                is_recording = False
                file_count = 0
                try:
                    # Count files modified in the last 5 minutes
                    result = subprocess.run(
                        ['find', camera_path, '-type', 'f', '-mmin', '-5'],
                        capture_output=True, text=True, timeout=3
                    )
                    recent_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
                    file_count = len(recent_files)
                    is_recording = file_count > 0
                except:
                    pass
                
                cameras.append({
                    'id': camera_id,
                    'name': camera_name,
                    'recording': is_recording,
                    'recording_count': file_count,
                    'last_recording': 'Active' if is_recording else 'Idle'
                })
        
        cameras.sort(key=lambda x: int(x['id']))
        return {'cameras': cameras, 'total': len(cameras), 'recording': sum(1 for c in cameras if c['recording'])}
    except:
        return {'cameras': [], 'total': 0, 'recording': 0}

def get_scrypted_events():
    # Count events from today
    today = datetime.now().strftime('%Y-%m-%d')
    today_events = 0
    week_events = 0
    
    try:
        # Quick check: count JSON files with ObjectDetector events from last 24 hours
        result = subprocess.run(
            ['find', '/scrypted/nvr/recordings', '-name', '*.json', '-mtime', '-1', '-exec', 
             'grep', '-l', 'ObjectDetector', '{}', '+'],
            capture_output=True, text=True, timeout=5
        )
        files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        today_events = len(files)
        
        # Week events
        result = subprocess.run(
            ['find', '/scrypted/nvr/recordings', '-name', '*.json', '-mtime', '-7', '-exec', 
             'grep', '-l', 'ObjectDetector', '{}', '+'],
            capture_output=True, text=True, timeout=5
        )
        files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        week_events = len(files)
    except:
        pass
    
    return {'today': today_events, 'week': week_events}

def get_scrypted_storage():
    try:
        result = subprocess.run(['du', '-sh', '/scrypted/nvr/recordings'], 
                                capture_output=True, text=True, timeout=3)
        size = result.stdout.split()[0] if result.returncode == 0 else 'N/A'
        
        # Count total recording files (all .rtsp and .json files)
        file_count = 0
        try:
            result = subprocess.run(
                ['find', '/scrypted/nvr/recordings', '-type', 'f', '(', '-name', '*.rtsp', '-o', '-name', '*.json', ')'],
                capture_output=True, text=True, timeout=5
            )
            files = result.stdout.strip().split('\n') if result.stdout.strip() else []
            file_count = len(files)
        except:
            pass
        
        return {'size': size, 'files': file_count}
    except:
        return {'size': 'N/A', 'files': 0}

def get_scrypted_container_stats():
    try:
        result = subprocess.run(['docker', 'inspect', 'scrypted', '--format', '{{.State.Status}}|{{.State.StartedAt}}'], 
                                capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            status, started_at = result.stdout.strip().split('|')
            start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            uptime_seconds = (datetime.now(start_time.tzinfo) - start_time).total_seconds()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            return {'status': status, 'uptime': f"{days}d {hours}h {minutes}m", 'started': start_time.strftime('%Y-%m-%d %H:%M:%S')}
        return {'status': 'unknown', 'uptime': 'N/A', 'started': 'N/A'}
    except:
        return {'status': 'error', 'uptime': 'N/A', 'started': 'N/A'}

def get_all_scrypted_stats():
    # Collect real Scrypted stats (cameras, events, storage, container)
    try:
        return {
            'cameras': get_scrypted_cameras(),
            'events': get_scrypted_events(),
            'storage': get_scrypted_storage(),
            'container': get_scrypted_container_stats()
        }
    except:
        return {
            'cameras': {'cameras': [], 'total': 0, 'recording': 0},
            'events': {'today': 0, 'week': 0},
            'storage': {'size': 'N/A', 'files': 0},
            'container': {'status': 'error', 'uptime': 'N/A', 'started': 'N/A'}
        }

if __name__ == '__main__':
    import json
    print(json.dumps(get_all_scrypted_stats(), indent=2))
