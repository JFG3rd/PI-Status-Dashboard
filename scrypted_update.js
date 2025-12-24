                    
                    // Scrypted Stats
                    if (data.scrypted && data.scrypted.container) {
                        document.getElementById('scryptedStatus').textContent = data.scrypted.container.status || 'unknown';
                        document.getElementById('scryptedUptime').textContent = data.scrypted.container.uptime || 'N/A';
                    }
                    
                    if (data.scrypted && data.scrypted.cameras) {
                        document.getElementById('scryptedCameras').textContent = data.scrypted.cameras.total || '0';
                        document.getElementById('scryptedRecording').textContent = data.scrypted.cameras.recording || '0';
                        
                        // Display camera list
                        const cameraListDiv = document.getElementById('cameraList');
                        if (data.scrypted.cameras.cameras && data.scrypted.cameras.cameras.length > 0) {
                            cameraListDiv.innerHTML = data.scrypted.cameras.cameras.map(camera => `
                                <div class="container-item">
                                    <div class="container-name">${camera.name}</div>
                                    <div class="stat">
                                        <span>Recording:</span>
                                        <span class="status-badge status-${camera.recording ? 'running' : 'stopped'}">${camera.recording ? 'Yes' : 'No'}</span>
                                    </div>
                                    <div class="stat">
                                        <span>Files:</span>
                                        <span>${camera.recording_count}</span>
                                    </div>
                                    <div class="stat">
                                        <span>Last:</span>
                                        <span>${camera.last_recording}</span>
                                    </div>
                                </div>
                            `).join('');
                        } else {
                            cameraListDiv.innerHTML = '<div style="text-align: center; opacity: 0.7;">No cameras found</div>';
                        }
                    }
                    
                    if (data.scrypted && data.scrypted.events) {
                        document.getElementById('scryptedEventsToday').textContent = data.scrypted.events.today || '0';
                        document.getElementById('scryptedEventsWeek').textContent = data.scrypted.events.week || '0';
                    }
                    
                    if (data.scrypted && data.scrypted.storage) {
                        document.getElementById('scryptedStorage').textContent = data.scrypted.storage.size || 'N/A';
                        document.getElementById('scryptedFiles').textContent = data.scrypted.storage.files || '0';
                    }
