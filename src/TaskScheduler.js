export class TaskScheduler {
    constructor(concurrency = 4) {
        this.concurrency = concurrency;
        this.queue = [];
        this.activeCount = 0;
        this.nextAllowedRequest = 0;
        this.isCancelled = false;
        this.timerId = null;
        if (typeof window !== 'undefined') {
            if (!window._schedulerMetrics) {
                window._schedulerMetrics = {
                    maxConcurrent: 0,
                    num429s: 0,
                    numRetries: 0,
                    numRetryExhausted: 0,
                    retryAfterValues: []
                };
            }
        }
    }

    async enqueue(taskFn, options = {}) {
        const retryCount = options.retryCount ?? 5;
        const onRetry = options.onRetry;
        
        return new Promise((resolve, reject) => {
            this.queue.push({ taskFn, resolve, reject, retryCount, onRetry });
            this.pump();
        });
    }

    cancelAll() {
        this.isCancelled = true;
        this.queue = [];
        if (this.timerId) {
            clearTimeout(this.timerId);
            this.timerId = null;
        }
    }

    async pump() {
        if (this.isCancelled) return;
        if (this.activeCount >= this.concurrency) return;
        if (this.queue.length === 0) return;

        const now = Date.now();
        if (now < this.nextAllowedRequest) {
            const delay = this.nextAllowedRequest - now;
            if (!this.timerId) {
                this.timerId = setTimeout(() => {
                    this.timerId = null;
                    this.pump();
                }, delay);
            }
            return;
        }

        const task = this.queue.shift();
        this.activeCount++;
        if (typeof window !== 'undefined' && window._schedulerMetrics) {
            window._schedulerMetrics.maxConcurrent = Math.max(window._schedulerMetrics.maxConcurrent, this.activeCount);
        }

        try {
            const result = await task.taskFn();
            task.resolve(result);
        } catch (err) {
            if (this.isCancelled) {
                task.reject(new Error('Upload cancelled'));
                return;
            }

            if (err.isRateLimit) {
                if (typeof window !== 'undefined' && window._schedulerMetrics) {
                    window._schedulerMetrics.num429s++;
                    window._schedulerMetrics.retryAfterValues.push(err.retryAfterSeconds);
                }
                // Update global gate
                const retryAfterMs = (err.retryAfterSeconds || 10) * 1000;
                const newAllowed = Date.now() + retryAfterMs;
                if (newAllowed > this.nextAllowedRequest) {
                    this.nextAllowedRequest = newAllowed;
                }
                
                if (task.retryCount > 0) {
                    task.retryCount--;
                    if (typeof window !== 'undefined' && window._schedulerMetrics) {
                        window._schedulerMetrics.numRetries++;
                    }
                    if (task.onRetry) task.onRetry();
                    // Re-enqueue at the front
                    this.queue.unshift(task);
                } else {
                    if (typeof window !== 'undefined' && window._schedulerMetrics) {
                        window._schedulerMetrics.numRetryExhausted++;
                    }
                    task.reject(new Error('Max retries exceeded'));
                }
            } else if (task.retryCount > 0 && err.message !== 'Upload cancelled' && !err?.message?.includes('already exists')) {
                // Generic error retry with backoff (jittered exponential)
                task.retryCount--;
                if (task.onRetry) task.onRetry();
                this.queue.push(task);
                
                // Add a small jittered delay globally so we don't immediately retry a failed non-429 request loop instantly
                const backoffMs = 1000 * Math.pow(2, 5 - task.retryCount) + Math.random() * 500;
                const newAllowed = Date.now() + backoffMs;
                if (newAllowed > this.nextAllowedRequest) {
                    this.nextAllowedRequest = newAllowed;
                }
            } else {
                task.reject(err);
            }
        } finally {
            this.activeCount--;
            this.pump();
        }
    }
}
