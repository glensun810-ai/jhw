/**
 * Progress Poller with Dynamic Intervals and Exponential Backoff
 * Replaces fixed 1-second polling with intelligent interval adjustment
 */
class ProgressPoller {
    constructor(executionId) {
        this.executionId = executionId;
        this.baseInterval = 2000;      // Base interval 2 seconds
        this.maxInterval = 5000;       // Max interval 5 seconds
        this.currentInterval = 2000;
        this.timeoutId = null;
        this.retryCount = 0;
        this.maxRetries = 3;
        this.completed = false;
        this.startTime = Date.now();
    }

    async start() {
        console.log(`开始轮询进度: ${this.executionId}`);
        await this.poll();
    }

    async poll() {
        if (this.completed) return;

        try {
            const response = await fetch(`/api/test-progress?executionId=${this.executionId}`);
            const data = await response.json();
            
            // Dynamic interval adjustment based on progress
            if (data.progress < 20) {
                this.currentInterval = 3000;  // Early stage: 3 seconds
            } else if (data.progress < 50) {
                this.currentInterval = 4000;  // Mid stage: 4 seconds
            } else if (data.progress < 80) {
                this.currentInterval = 5000;  // Later stage: 5 seconds
            } else if (data.progress < 100) {
                this.currentInterval = 6000;  // Near completion: 6 seconds
            } else {
                console.log('测试完成，停止轮询');
                this.completed = true;
                this.onComplete(data);
                return;
            }
            
            this.retryCount = 0;  // Reset retry count on success
            this.onProgress(data);
            
            // Continue polling with adjusted interval
            this.timeoutId = setTimeout(() => this.poll(), this.currentInterval);
            
        } catch (error) {
            console.error('轮询失败:', error);
            this.retryCount++;
            
            if (this.retryCount <= this.maxRetries) {
                // Exponential backoff: 2s, 4s, 8s (capped at maxInterval)
                const backoffTime = Math.min(this.maxInterval, 2000 * Math.pow(2, this.retryCount - 1));
                console.log(`轮询失败，${backoffTime/1000}秒后重试 (${this.retryCount}/${this.maxRetries})`);
                this.timeoutId = setTimeout(() => this.poll(), backoffTime);
            } else {
                console.error('轮询失败次数过多，停止轮询');
                this.onError(new Error('获取进度失败，请刷新页面重试'));
            }
        }
    }

    stop() {
        if (this.timeoutId) {
            clearTimeout(this.timeoutId);
            this.timeoutId = null;
        }
        this.completed = true;
    }

    onProgress(data) {
        // To be overridden by caller
        console.log(`进度: ${data.progress}%`);
    }

    onComplete(results) {
        // To be overridden by caller
        console.log('测试完成', results);
    }

    onError(error) {
        // To be overridden by caller
        console.error(error);
    }
}

// Example usage in the frontend
function startBrandTestWithOptimizedPolling(brandData) {
    // Show loading state
    showLoading('正在启动品牌测试...');
    
    // Start the brand test
    fetch('/api/perform-brand-test', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(brandData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.executionId) {
            hideLoading();
            
            // Initialize progress poller with dynamic intervals
            const poller = new ProgressPoller(data.executionId);
            
            // Set up progress callbacks
            poller.onProgress = (progressData) => {
                // Update progress bar
                const progressBar = document.getElementById('progress-bar');
                const progressText = document.getElementById('progress-text');
                
                if (progressBar) {
                    progressBar.style.width = `${progressData.progress}%`;
                }
                if (progressText) {
                    progressText.innerText = `${progressData.progress}%`;
                }
                
                // Update status text
                const statusElement = document.getElementById('status-text');
                if (statusElement) {
                    statusElement.innerText = progressData.status || '进行中...';
                }
            };
            
            poller.onComplete = (results) => {
                showToast('品牌测试完成', 'success');
                renderResults(results);
                // Optionally redirect to results page
                // window.location.href = `/results/${data.executionId}`;
            };
            
            poller.onError = (error) => {
                showToast(`测试过程中出现错误: ${error.message}`, 'error');
                console.error('Polling error:', error);
            };
            
            // Start polling with optimized intervals
            poller.start();
        } else {
            hideLoading();
            showToast('启动测试失败，请重试', 'error');
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error starting brand test:', error);
        showToast('启动测试时发生错误', 'error');
    });
}

// WebSocket alternative implementation (for future enhancement)
class WebSocketProgressTracker {
    constructor(executionId) {
        this.executionId = executionId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }
    
    connect() {
        // Construct WebSocket URL (adjust based on your backend WebSocket implementation)
        const wsUrl = `ws://${window.location.host}/ws/progress/${this.executionId}`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('WebSocket connection opened for progress tracking');
                this.reconnectAttempts = 0;
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleProgressUpdate(data);
                } catch (e) {
                    console.error('Error parsing WebSocket message:', e);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket connection closed:', event.code, event.reason);
                
                // Attempt to reconnect if connection was not closed intentionally
                if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    const delay = Math.min(30000, 1000 * Math.pow(2, this.reconnectAttempts));
                    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    
                    setTimeout(() => {
                        this.connect();
                    }, delay);
                }
            };
        } catch (e) {
            console.error('Failed to create WebSocket connection:', e);
        }
    }
    
    handleProgressUpdate(data) {
        // Handle progress update from WebSocket
        if (data.type === 'progress_update') {
            // Update UI with progress data
            const progressBar = document.getElementById('progress-bar');
            const progressText = document.getElementById('progress-text');
            
            if (progressBar) {
                progressBar.style.width = `${data.progress}%`;
            }
            if (progressText) {
                progressText.innerText = `${data.progress}%`;
            }
            
            // If complete, handle completion
            if (data.progress >= 100) {
                this.handleCompletion(data.results);
            }
        }
    }
    
    handleCompletion(results) {
        // Handle completion event
        showToast('品牌测试完成', 'success');
        renderResults(results);
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close(1000, "Client disconnected");
            this.ws = null;
        }
    }
}

// Utility functions for UI updates
function showLoading(message = '处理中...') {
    const loader = document.getElementById('loading-indicator');
    if (loader) {
        loader.style.display = 'block';
        loader.querySelector('.loading-text')?.textContent = message;
    }
}

function hideLoading() {
    const loader = document.getElementById('loading-indicator');
    if (loader) {
        loader.style.display = 'none';
    }
}

function showToast(message, type = 'info') {
    // Create and show toast notification
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        display: flex;
        flex-direction: column;
        gap: 10px;
    `;
    document.body.appendChild(container);
    return container;
}

function renderResults(results) {
    // Render the test results to the UI
    console.log('Rendering results:', results);
    
    // Example implementation - adjust based on your UI
    const resultsContainer = document.getElementById('results-container');
    if (resultsContainer) {
        resultsContainer.innerHTML = `
            <h3>测试结果</h3>
            <p>整体得分: ${results.main_brand?.overallScore || 0}</p>
            <p>品牌权威度: ${results.main_brand?.overallAuthority || 0}</p>
            <p>品牌可见度: ${results.main_brand?.overallVisibility || 0}</p>
            <!-- Add more result fields as needed -->
        `;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ProgressPoller, WebSocketProgressTracker };
}