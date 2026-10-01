'use strict';

const EventEmitter = require('events');

/**
 * A dependency-free async task queue with bounded concurrency, priorities,
 * per-task timeout/retry, pause/resume and cancellation support.
 * Generated & Optimized by Claude Code
 */
class ConcurrencyQueue extends EventEmitter {
  constructor(options = {}) {
    super();

    const {
      concurrency = 1,
      autoStart = true,
      timeout,
      retries = 0,
      retryDelay = (attempt) => Math.min(1000 * 2 ** (attempt - 1), 30000),
      throwOnTimeout = true,
    } = options;

    if (!Number.isInteger(concurrency) || concurrency < 1) {
      throw new TypeError('concurrency must be an integer >= 1');
    }

    this._concurrency = concurrency;
    this._defaultTimeout = timeout;
    this._defaultRetries = retries;
    this._retryDelay = retryDelay;
    this._throwOnTimeout = throwOnTimeout;

    this._queue = [];
    this._sequence = 0;
    this._running = 0;
    this._paused = !autoStart;

    this._idleWaiters = [];
    this._emptyWaiters = [];
  }

  get size() { return this._queue.length; }
  get pending() { return this._running; }
  get isPaused() { return this._paused; }
  get concurrency() { return this._concurrency; }

  set concurrency(value) {
    if (!Number.isInteger(value) || value < 1) {
      throw new TypeError('concurrency must be an integer >= 1');
    }
    this._concurrency = value;
    this._drain();
  }

  add(task, options = {}) {
    if (typeof task !== 'function') {
      throw new TypeError('task must be a function');
    }
    const {
      priority = 0,
      timeout = this._defaultTimeout,
      retries = this._defaultRetries,
      signal,
    } = options;

    if (signal?.aborted) {
      return Promise.reject(signal.reason ?? new Error('Task aborted before it started'));
    }

    return new Promise((resolve, reject) => {
      const entry = {
        task, priority, timeout, retries, signal,
        seq: this._sequence++,
        resolve, reject,
      };

      if (signal) {
        const onAbort = () => {
          const index = this._queue.indexOf(entry);
          if (index !== -1) {
            this._queue.splice(index, 1);
            reject(signal.reason ?? new Error('Task aborted before it started'));
            this._checkEmpty();
          }
        };
        signal.addEventListener('abort', onAbort, { once: true });
        entry.cleanupSignal = () => signal.removeEventListener('abort', onAbort);
      }

      this._insertSorted(entry);
      this.emit('add');
      this._drain();
    });
  }

  addAll(tasks, options = {}) {
    return Promise.all(tasks.map((task) => this.add(task, options)));
  }

  pause() { this._paused = true; }

  start() {
    this._paused = false;
    this._drain();
  }

  clear() {
    const dropped = this._queue;
    this._queue = [];
    for (const entry of dropped) {
      entry.cleanupSignal?.();
      entry.reject(new Error('Task cancelled: queue cleared'));
    }
    this._checkEmpty();
  }

  onEmpty() {
    if (this._queue.length === 0) return Promise.resolve();
    return new Promise((resolve) => this._emptyWaiters.push(resolve));
  }

  onIdle() {
    if (this._queue.length === 0 && this._running === 0) return Promise.resolve();
    return new Promise((resolve) => this._idleWaiters.push(resolve));
  }

  _insertSorted(entry) {
    let low = 0;
    let high = this._queue.length;
    while (low < high) {
      const mid = (low + high) >>> 1;
      const other = this._queue[mid];
      if (other.priority > entry.priority || (other.priority === entry.priority && other.seq < entry.seq)) {
        low = mid + 1;
      } else {
        high = mid;
      }
    }
    this._queue.splice(low, 0, entry);
  }

  _drain() {
    if (this._paused) return;
    while (this._running < this._concurrency && this._queue.length > 0) {
      const entry = this._queue.shift();
      this._checkEmpty();
      this._run(entry);
    }
  }

  async _run(entry, attempt = 0) {
    entry.cleanupSignal?.();
    this._running++;
    this.emit('active', { pending: this._running, size: this._queue.length });

    let timer;
    try {
      const result = await new Promise((resolve, reject) => {
        if (entry.timeout) {
          timer = setTimeout(() => {
            reject(new Error(`Task timed out after ${entry.timeout}ms`));
          }, entry.timeout);
        }
        Promise.resolve()
          .then(() => entry.task(entry.signal))
          .then(resolve, reject);
      });
      clearTimeout(timer);
      entry.resolve(result);
      this.emit('completed', result);
    } catch (err) {
      clearTimeout(timer);
      const canRetry = attempt < entry.retries && !entry.signal?.aborted;

      if (canRetry) {
        this._running--;
        const delay = this._retryDelay(attempt + 1);
        this.emit('retry', { error: err, attempt: attempt + 1 });
        setTimeout(() => this._run(entry, attempt + 1), delay);
        this._drain();
        this._checkIdle();
        return;
      }

      const isTimeout = err instanceof Error && /timed out/.test(err.message);
      if (isTimeout && !this._throwOnTimeout) {
        entry.resolve(undefined);
      } else {
        entry.reject(err);
        this.emit('error', err);
      }
    }

    this._running--;
    this._drain();
    this._checkIdle();
  }

  _checkEmpty() {
    if (this._queue.length === 0) {
      const waiters = this._emptyWaiters;
      this._emptyWaiters = [];
      waiters.forEach((resolve) => resolve());
      this.emit('empty');
    }
  }

  _checkIdle() {
    if (this._queue.length === 0 && this._running === 0) {
      const waiters = this._idleWaiters;
      this._idleWaiters = [];
      waiters.forEach((resolve) => resolve());
      this.emit('idle');
    }
  }
}

module.exports = ConcurrencyQueue;
