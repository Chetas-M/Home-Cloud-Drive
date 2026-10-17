// test_scheduler.js
// Run with: node test_scheduler.js

import { TaskScheduler } from './src/TaskScheduler.js';

// Mock RateLimitError
class RateLimitError extends Error {
    constructor(retryAfterSeconds = 1) {
        super('Too many attempts.');
        this.name = 'RateLimitError';
        this.retryAfterSeconds = retryAfterSeconds;
        this.isRateLimit = true;
    }
}

async function runTests() {
    console.log("=== Running TaskScheduler Frontend Simulation ===\n");

    let passCount = 0;
    let failCount = 0;

    function assert(condition, message) {
        if (!condition) {
            console.error("❌ FAILED: " + message);
            failCount++;
            throw new Error(message);
        } else {
            console.log("✅ PASSED: " + message);
            passCount++;
        }
    }

    // --- TEST 1: Concurrency and 675 Tasks ---
    console.log("Test 1: 675 tasks with Max Concurrency = 4");
    let scheduler1 = new TaskScheduler(4);
    let activeTasks1 = 0;
    let maxObservedActive1 = 0;
    let completed1 = 0;
    
    let promises1 = [];
    for (let i = 0; i < 675; i++) {
        promises1.push(scheduler1.enqueue(async () => {
            activeTasks1++;
            if (activeTasks1 > maxObservedActive1) {
                maxObservedActive1 = activeTasks1;
            }
            // simulate fast work
            await new Promise(r => setTimeout(r, 1));
            activeTasks1--;
            completed1++;
            return i;
        }));
    }
    await Promise.all(promises1);
    assert(maxObservedActive1 === 4, `Max concurrency should be exactly 4 (was ${maxObservedActive1})`);
    assert(completed1 === 675, `All 675 tasks should complete (was ${completed1})`);


    // --- TEST 2: Global 429 Gate & Retry-After ---
    console.log("\nTest 2: Global 429 Gate & Retry-After");
    let scheduler2 = new TaskScheduler(2);
    let tasksCompleted2 = 0;
    let rateLimitHits = 0;
    let startTime2 = Date.now();
    let promises2 = [];

    for (let i = 0; i < 5; i++) {
        promises2.push(scheduler2.enqueue(async () => {
            if (i === 0 && rateLimitHits === 0) {
                rateLimitHits++;
                throw new RateLimitError(1); // 1 second retry after
            }
            tasksCompleted2++;
        }, { retryCount: 3 }));
    }

    await Promise.all(promises2);
    let elapsed2 = Date.now() - startTime2;
    assert(tasksCompleted2 === 5, `All 5 tasks should eventually complete (was ${tasksCompleted2})`);
    assert(rateLimitHits === 1, `Should hit rate limit once`);
    assert(elapsed2 >= 1000, `Should have paused for at least 1000ms due to Retry-After (took ${elapsed2}ms)`);


    // --- TEST 3: Retry Exhaustion & Permanent Failure ---
    console.log("\nTest 3: Retry Exhaustion while others complete");
    let scheduler3 = new TaskScheduler(2);
    let successes3 = 0;
    let failures3 = 0;
    
    let promises3 = [];
    for (let i = 0; i < 3; i++) {
        promises3.push(scheduler3.enqueue(async () => {
            if (i === 1) {
                let err = new Error("Permanent simulated failure");
                err.isRateLimit = true;
                err.retryAfterSeconds = 0.05; // 50ms delay for fast test
                throw err;
            }
            successes3++;
        }, { retryCount: 2 }).catch(err => {
            failures3++;
            if (err.message !== 'Max retries exceeded') throw err;
        }));
    }
    
    await Promise.all(promises3);
    assert(successes3 === 2, `2 tasks should succeed (was ${successes3})`);
    assert(failures3 === 1, `1 task should fail permanently after retries exhausted (was ${failures3})`);


    // --- TEST 4: Cancellation ---
    console.log("\nTest 4: Cancellation");
    let scheduler4 = new TaskScheduler(1);
    let successes4 = 0;
    let cancelled4 = 0;
    
    let p1 = scheduler4.enqueue(async () => { await new Promise(r => setTimeout(r, 50)); successes4++; }).catch(e => {});
    let p2 = scheduler4.enqueue(async () => { successes4++; }).catch(e => {
        if (e.message === 'Upload cancelled') cancelled4++;
    }); // Should never start
    
    setTimeout(() => {
        scheduler4.cancelAll();
    }, 10);
    
    await Promise.all([p1, p2]);
    
    assert(successes4 === 0 || successes4 === 1, "Cancelled tasks shouldn't complete un-started");
    assert(cancelled4 === 1, "Queued task should be cancelled with 'Upload cancelled'");


    console.log(`\n=== All tests passed! (${passCount}/${passCount+failCount}) ===`);
}

runTests().catch(console.error);
