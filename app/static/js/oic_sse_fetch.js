/**
 * oic_sse_fetch.js
 *
 * Drop-in replacement for fetch() used by OIC chat and scenario-refinement
 * endpoints that return Server-Sent Events (SSE) to keep mobile connections
 * alive during long AI operations (60-180 s).
 *
 * Usage:
 *   const data = await oicSseFetch('/api/chat', { method: 'POST', body: JSON.stringify(payload) });
 *   // data is the parsed JSON from the server's "result" event — identical to
 *   // what a plain fetch().then(r => r.json()) would have returned.
 *
 * Protocol (must match _run_with_sse_keepalive in main.py):
 *   event: keepalive   empty data — ignored, just resets the connection timer
 *   event: result      JSON payload — resolved as the Promise value
 *   event: error       JSON {"error": "..."} — rejected as an Error
 *
 * Falls back gracefully:
 *   If the server returns a non-SSE content-type (e.g. during local dev
 *   without the Accept header being respected) the raw JSON is returned
 *   normally, so the same call site works against both SSE and plain-JSON
 *   endpoints without changes.
 */

/**
 * @param {string} url
 * @param {RequestInit} [options]   Same options as fetch().  The Accept header
 *                                  is automatically set to prefer SSE.
 * @returns {Promise<any>}          Resolved with the parsed JSON payload.
 */
async function oicSseFetch(url, options = {}) {
    const headers = Object.assign({}, options.headers || {}, {
        'Accept': 'text/event-stream',
        'Content-Type': options.headers?.['Content-Type'] || 'application/json',
    });

    const response = await fetch(url, Object.assign({}, options, { headers }));

    if (!response.ok) {
        // Surface HTTP errors (4xx/5xx) before trying to read the body
        let errMsg = `HTTP ${response.status}`;
        try { const j = await response.json(); errMsg = j.error || errMsg; } catch (_) {}
        throw new Error(errMsg);
    }

    const contentType = response.headers.get('Content-Type') || '';

    // --- Plain JSON fallback (server doesn't support SSE or test env) ---
    if (!contentType.includes('text/event-stream')) {
        return response.json();
    }

    // --- SSE path ---
    return new Promise((resolve, reject) => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        function processBuffer() {
            // SSE frames are separated by double newline
            const frames = buffer.split('\n\n');
            // Keep the last incomplete frame in the buffer
            buffer = frames.pop();

            for (const frame of frames) {
                if (!frame.trim()) continue;

                let eventType = 'message';
                let dataLine = '';

                for (const line of frame.split('\n')) {
                    if (line.startsWith('event:')) {
                        eventType = line.slice(6).trim();
                    } else if (line.startsWith('data:')) {
                        dataLine = line.slice(5).trim();
                    }
                }

                if (eventType === 'keepalive') {
                    // Nothing to do — connection is alive
                    continue;
                }

                if (eventType === 'result') {
                    try {
                        resolve(JSON.parse(dataLine));
                    } catch (e) {
                        reject(new Error('SSE result parse error: ' + e.message));
                    }
                    return; // stream complete
                }

                if (eventType === 'error') {
                    let msg = 'Server error';
                    try { msg = JSON.parse(dataLine).error || msg; } catch (_) {}
                    reject(new Error(msg));
                    return;
                }
            }
        }

        function read() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    // Stream ended — process any remaining buffer
                    if (buffer.trim()) {
                        buffer += '\n\n';
                        processBuffer();
                    }
                    // If we never resolved, the stream ended unexpectedly
                    reject(new Error('SSE stream ended without a result event'));
                    return;
                }
                buffer += decoder.decode(value, { stream: true });
                processBuffer();
                read();
            }).catch(reject);
        }

        read();
    });
}

// Make available as a module export and as a global (both usage patterns exist
// in this codebase: inline scripts and the chat_sidebar.js module pattern).
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { oicSseFetch };
}
