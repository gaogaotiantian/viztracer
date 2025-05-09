var service_worker = (function () {
'use strict';

var service_worker = {};

Object.defineProperty(service_worker, "__esModule", { value: true });
const LOG_TAG = `ServiceWorker: `;
const CACHE_NAME = 'ui-perfetto-dev';
const OPEN_TRACE_PREFIX = '/_open_trace';
const INDEX_TIMEOUT_MS = 3000;
const INSTALL_TIMEOUT_MS = 30000;
let postedFiles = new Map();
self.addEventListener('install', (event) => {
    const doInstall = async () => {
        let bypass = true;
        try {
            bypass = await caches.has('BYPASS_SERVICE_WORKER');
        }
        catch (_) {
        }
        if (bypass) {
            throw new Error(LOG_TAG + 'skipping installation, bypass enabled');
        }
        try {
            for (const key of await caches.keys()) {
                if (key.startsWith('dist-')) {
                    await caches.delete(key);
                }
            }
        }
        catch (_) {
        }
        const match = /\bv=([\w.-]*)/.exec(location.search);
        if (!match) {
            throw new Error('Failed to install. Was epecting a query string like ' +
                `?v=v1.2-sha query string, got "${location.search}" instead`);
        }
        await installAppVersionIntoCache(match[1]);
        self.skipWaiting();
    };
    event.waitUntil(doInstall());
});
self.addEventListener('activate', (event) => {
    console.info(LOG_TAG + 'activated');
    const doActivate = async () => {
        await self.clients.claim();
    };
    event.waitUntil(doActivate());
});
self.addEventListener('fetch', (event) => {
    if (!shouldHandleHttpRequest(event.request)) {
        console.debug(LOG_TAG + `serving ${event.request.url} from network`);
        return;
    }
    event.respondWith(handleHttpRequest(event.request));
});
function shouldHandleHttpRequest(req) {
    if (req.cache === 'only-if-cached' && req.mode !== 'same-origin') {
        return false;
    }
    const url = new URL(req.url);
    if (url.pathname === '/live_reload')
        return false;
    if (url.pathname.startsWith(OPEN_TRACE_PREFIX))
        return true;
    return req.method === 'GET' && url.origin === self.location.origin;
}
async function handleHttpRequest(req) {
    if (!shouldHandleHttpRequest(req)) {
        throw new Error(LOG_TAG + `${req.url} shouldn't have been handled`);
    }
    const cacheOps = { cacheName: CACHE_NAME };
    const url = new URL(req.url);
    if (url.pathname === '/') {
        try {
            console.debug(LOG_TAG + `Fetching live ${req.url}`);
            return await fetchWithTimeout(req, INDEX_TIMEOUT_MS);
        }
        catch (err) {
            console.warn(LOG_TAG + `Failed to fetch ${req.url}, using cache.`, err);
        }
    }
    else if (url.pathname === '/offline') {
        const cachedRes = await caches.match(new Request('/'), cacheOps);
        if (cachedRes)
            return cachedRes;
    }
    else if (url.pathname.startsWith(OPEN_TRACE_PREFIX)) {
        return await handleOpenTraceRequest(req);
    }
    const cachedRes = await caches.match(req, cacheOps);
    if (cachedRes) {
        console.debug(LOG_TAG + `serving ${req.url} from cache`);
        return cachedRes;
    }
    console.warn(LOG_TAG + `cache miss on ${req.url}, using live network`);
    return fetch(req);
}
async function handleOpenTraceRequest(req) {
    const url = new URL(req.url);
    console.assert(url.pathname.startsWith(OPEN_TRACE_PREFIX));
    const fileKey = url.pathname.substring(OPEN_TRACE_PREFIX.length);
    if (req.method === 'POST') {
        const formData = await req.formData();
        const qsParams = new URLSearchParams();
        formData.forEach((value, key) => {
            if (key === 'trace') {
                if (value instanceof File) {
                    postedFiles.set(fileKey, value);
                    qsParams.set('url', req.url);
                }
                return;
            }
            qsParams.set(key, `${value}`);
        });
        return Response.redirect(`${url.protocol}//${url.host}/#!/?${qsParams}`);
    }
    const file = postedFiles.get(fileKey);
    if (file !== undefined) {
        postedFiles.delete(fileKey);
        return new Response(file);
    }
    return Response.error();
}
async function installAppVersionIntoCache(version) {
    const manifestUrl = `${version}/manifest.json`;
    try {
        console.log(LOG_TAG + `Starting installation of ${manifestUrl}`);
        await caches.delete(CACHE_NAME);
        const resp = await fetchWithTimeout(manifestUrl, INSTALL_TIMEOUT_MS);
        const manifest = await resp.json();
        const manifestResources = manifest['resources'];
        if (!manifestResources || !(manifestResources instanceof Object)) {
            throw new Error(`Invalid manifest ${manifestUrl} : ${manifest}`);
        }
        const cache = await caches.open(CACHE_NAME);
        const urlsToCache = [];
        urlsToCache.push(new Request('/', { cache: 'reload', mode: 'same-origin' }));
        for (const [resource, integrity] of Object.entries(manifestResources)) {
            const reqOpts = {
                cache: 'no-cache',
                mode: 'same-origin',
                integrity: `${integrity}`,
            };
            urlsToCache.push(new Request(`${version}/${resource}`, reqOpts));
        }
        await cache.addAll(urlsToCache);
        console.log(LOG_TAG + 'installation completed for ' + version);
    }
    catch (err) {
        console.error(LOG_TAG + `Installation failed for ${manifestUrl}`, err);
        await caches.delete(CACHE_NAME);
        throw err;
    }
}
function fetchWithTimeout(req, timeoutMs) {
    const url = req.url || `${req}`;
    return new Promise((resolve, reject) => {
        const timerId = setTimeout(() => {
            reject(new Error(`Timed out while fetching ${url}`));
        }, timeoutMs);
        fetch(req).then((resp) => {
            clearTimeout(timerId);
            if (resp.ok) {
                resolve(resp);
            }
            else {
                reject(new Error(`Fetch failed for ${url}: ${resp.status} ${resp.statusText}`));
            }
        }, reject);
    });
}

return service_worker;

})();
//# sourceMappingURL=service_worker.js.map
