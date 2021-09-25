var service_worker = (function () {
'use strict';

var commonjsGlobal = typeof globalThis !== 'undefined' ? globalThis : typeof window !== 'undefined' ? window : typeof global !== 'undefined' ? global : typeof self !== 'undefined' ? self : {};

function createCommonjsModule(fn, basedir, module) {
	return module = {
	  path: basedir,
	  exports: {},
	  require: function (path, base) {
      return commonjsRequire(path, (base === undefined || base === null) ? module.path : base);
    }
	}, fn(module, module.exports), module.exports;
}

function commonjsRequire () {
	throw new Error('Dynamic requires are not currently supported by @rollup/plugin-commonjs');
}

var tslib = createCommonjsModule(function (module) {
/*! *****************************************************************************
Copyright (c) Microsoft Corporation.

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR
OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
PERFORMANCE OF THIS SOFTWARE.
***************************************************************************** */
/* global global, define, System, Reflect, Promise */
var __extends;
var __assign;
var __rest;
var __decorate;
var __param;
var __metadata;
var __awaiter;
var __generator;
var __exportStar;
var __values;
var __read;
var __spread;
var __spreadArrays;
var __spreadArray;
var __await;
var __asyncGenerator;
var __asyncDelegator;
var __asyncValues;
var __makeTemplateObject;
var __importStar;
var __importDefault;
var __classPrivateFieldGet;
var __classPrivateFieldSet;
var __createBinding;
(function (factory) {
    var root = typeof commonjsGlobal === "object" ? commonjsGlobal : typeof self === "object" ? self : typeof this === "object" ? this : {};
    {
        factory(createExporter(root, createExporter(module.exports)));
    }
    function createExporter(exports, previous) {
        if (exports !== root) {
            if (typeof Object.create === "function") {
                Object.defineProperty(exports, "__esModule", { value: true });
            }
            else {
                exports.__esModule = true;
            }
        }
        return function (id, v) { return exports[id] = previous ? previous(id, v) : v; };
    }
})
(function (exporter) {
    var extendStatics = Object.setPrototypeOf ||
        ({ __proto__: [] } instanceof Array && function (d, b) { d.__proto__ = b; }) ||
        function (d, b) { for (var p in b) if (Object.prototype.hasOwnProperty.call(b, p)) d[p] = b[p]; };

    __extends = function (d, b) {
        if (typeof b !== "function" && b !== null)
            throw new TypeError("Class extends value " + String(b) + " is not a constructor or null");
        extendStatics(d, b);
        function __() { this.constructor = d; }
        d.prototype = b === null ? Object.create(b) : (__.prototype = b.prototype, new __());
    };

    __assign = Object.assign || function (t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p)) t[p] = s[p];
        }
        return t;
    };

    __rest = function (s, e) {
        var t = {};
        for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p) && e.indexOf(p) < 0)
            t[p] = s[p];
        if (s != null && typeof Object.getOwnPropertySymbols === "function")
            for (var i = 0, p = Object.getOwnPropertySymbols(s); i < p.length; i++) {
                if (e.indexOf(p[i]) < 0 && Object.prototype.propertyIsEnumerable.call(s, p[i]))
                    t[p[i]] = s[p[i]];
            }
        return t;
    };

    __decorate = function (decorators, target, key, desc) {
        var c = arguments.length, r = c < 3 ? target : desc === null ? desc = Object.getOwnPropertyDescriptor(target, key) : desc, d;
        if (typeof Reflect === "object" && typeof Reflect.decorate === "function") r = Reflect.decorate(decorators, target, key, desc);
        else for (var i = decorators.length - 1; i >= 0; i--) if (d = decorators[i]) r = (c < 3 ? d(r) : c > 3 ? d(target, key, r) : d(target, key)) || r;
        return c > 3 && r && Object.defineProperty(target, key, r), r;
    };

    __param = function (paramIndex, decorator) {
        return function (target, key) { decorator(target, key, paramIndex); }
    };

    __metadata = function (metadataKey, metadataValue) {
        if (typeof Reflect === "object" && typeof Reflect.metadata === "function") return Reflect.metadata(metadataKey, metadataValue);
    };

    __awaiter = function (thisArg, _arguments, P, generator) {
        function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
        return new (P || (P = Promise))(function (resolve, reject) {
            function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
            function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
            function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
            step((generator = generator.apply(thisArg, _arguments || [])).next());
        });
    };

    __generator = function (thisArg, body) {
        var _ = { label: 0, sent: function() { if (t[0] & 1) throw t[1]; return t[1]; }, trys: [], ops: [] }, f, y, t, g;
        return g = { next: verb(0), "throw": verb(1), "return": verb(2) }, typeof Symbol === "function" && (g[Symbol.iterator] = function() { return this; }), g;
        function verb(n) { return function (v) { return step([n, v]); }; }
        function step(op) {
            if (f) throw new TypeError("Generator is already executing.");
            while (_) try {
                if (f = 1, y && (t = op[0] & 2 ? y["return"] : op[0] ? y["throw"] || ((t = y["return"]) && t.call(y), 0) : y.next) && !(t = t.call(y, op[1])).done) return t;
                if (y = 0, t) op = [op[0] & 2, t.value];
                switch (op[0]) {
                    case 0: case 1: t = op; break;
                    case 4: _.label++; return { value: op[1], done: false };
                    case 5: _.label++; y = op[1]; op = [0]; continue;
                    case 7: op = _.ops.pop(); _.trys.pop(); continue;
                    default:
                        if (!(t = _.trys, t = t.length > 0 && t[t.length - 1]) && (op[0] === 6 || op[0] === 2)) { _ = 0; continue; }
                        if (op[0] === 3 && (!t || (op[1] > t[0] && op[1] < t[3]))) { _.label = op[1]; break; }
                        if (op[0] === 6 && _.label < t[1]) { _.label = t[1]; t = op; break; }
                        if (t && _.label < t[2]) { _.label = t[2]; _.ops.push(op); break; }
                        if (t[2]) _.ops.pop();
                        _.trys.pop(); continue;
                }
                op = body.call(thisArg, _);
            } catch (e) { op = [6, e]; y = 0; } finally { f = t = 0; }
            if (op[0] & 5) throw op[1]; return { value: op[0] ? op[1] : void 0, done: true };
        }
    };

    __exportStar = function(m, o) {
        for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(o, p)) __createBinding(o, m, p);
    };

    __createBinding = Object.create ? (function(o, m, k, k2) {
        if (k2 === undefined) k2 = k;
        Object.defineProperty(o, k2, { enumerable: true, get: function() { return m[k]; } });
    }) : (function(o, m, k, k2) {
        if (k2 === undefined) k2 = k;
        o[k2] = m[k];
    });

    __values = function (o) {
        var s = typeof Symbol === "function" && Symbol.iterator, m = s && o[s], i = 0;
        if (m) return m.call(o);
        if (o && typeof o.length === "number") return {
            next: function () {
                if (o && i >= o.length) o = void 0;
                return { value: o && o[i++], done: !o };
            }
        };
        throw new TypeError(s ? "Object is not iterable." : "Symbol.iterator is not defined.");
    };

    __read = function (o, n) {
        var m = typeof Symbol === "function" && o[Symbol.iterator];
        if (!m) return o;
        var i = m.call(o), r, ar = [], e;
        try {
            while ((n === void 0 || n-- > 0) && !(r = i.next()).done) ar.push(r.value);
        }
        catch (error) { e = { error: error }; }
        finally {
            try {
                if (r && !r.done && (m = i["return"])) m.call(i);
            }
            finally { if (e) throw e.error; }
        }
        return ar;
    };

    /** @deprecated */
    __spread = function () {
        for (var ar = [], i = 0; i < arguments.length; i++)
            ar = ar.concat(__read(arguments[i]));
        return ar;
    };

    /** @deprecated */
    __spreadArrays = function () {
        for (var s = 0, i = 0, il = arguments.length; i < il; i++) s += arguments[i].length;
        for (var r = Array(s), k = 0, i = 0; i < il; i++)
            for (var a = arguments[i], j = 0, jl = a.length; j < jl; j++, k++)
                r[k] = a[j];
        return r;
    };

    __spreadArray = function (to, from) {
        for (var i = 0, il = from.length, j = to.length; i < il; i++, j++)
            to[j] = from[i];
        return to;
    };

    __await = function (v) {
        return this instanceof __await ? (this.v = v, this) : new __await(v);
    };

    __asyncGenerator = function (thisArg, _arguments, generator) {
        if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
        var g = generator.apply(thisArg, _arguments || []), i, q = [];
        return i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function () { return this; }, i;
        function verb(n) { if (g[n]) i[n] = function (v) { return new Promise(function (a, b) { q.push([n, v, a, b]) > 1 || resume(n, v); }); }; }
        function resume(n, v) { try { step(g[n](v)); } catch (e) { settle(q[0][3], e); } }
        function step(r) { r.value instanceof __await ? Promise.resolve(r.value.v).then(fulfill, reject) : settle(q[0][2], r);  }
        function fulfill(value) { resume("next", value); }
        function reject(value) { resume("throw", value); }
        function settle(f, v) { if (f(v), q.shift(), q.length) resume(q[0][0], q[0][1]); }
    };

    __asyncDelegator = function (o) {
        var i, p;
        return i = {}, verb("next"), verb("throw", function (e) { throw e; }), verb("return"), i[Symbol.iterator] = function () { return this; }, i;
        function verb(n, f) { i[n] = o[n] ? function (v) { return (p = !p) ? { value: __await(o[n](v)), done: n === "return" } : f ? f(v) : v; } : f; }
    };

    __asyncValues = function (o) {
        if (!Symbol.asyncIterator) throw new TypeError("Symbol.asyncIterator is not defined.");
        var m = o[Symbol.asyncIterator], i;
        return m ? m.call(o) : (o = typeof __values === "function" ? __values(o) : o[Symbol.iterator](), i = {}, verb("next"), verb("throw"), verb("return"), i[Symbol.asyncIterator] = function () { return this; }, i);
        function verb(n) { i[n] = o[n] && function (v) { return new Promise(function (resolve, reject) { v = o[n](v), settle(resolve, reject, v.done, v.value); }); }; }
        function settle(resolve, reject, d, v) { Promise.resolve(v).then(function(v) { resolve({ value: v, done: d }); }, reject); }
    };

    __makeTemplateObject = function (cooked, raw) {
        if (Object.defineProperty) { Object.defineProperty(cooked, "raw", { value: raw }); } else { cooked.raw = raw; }
        return cooked;
    };

    var __setModuleDefault = Object.create ? (function(o, v) {
        Object.defineProperty(o, "default", { enumerable: true, value: v });
    }) : function(o, v) {
        o["default"] = v;
    };

    __importStar = function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k in mod) if (k !== "default" && Object.prototype.hasOwnProperty.call(mod, k)) __createBinding(result, mod, k);
        __setModuleDefault(result, mod);
        return result;
    };

    __importDefault = function (mod) {
        return (mod && mod.__esModule) ? mod : { "default": mod };
    };

    __classPrivateFieldGet = function (receiver, state, kind, f) {
        if (kind === "a" && !f) throw new TypeError("Private accessor was defined without a getter");
        if (typeof state === "function" ? receiver !== state || !f : !state.has(receiver)) throw new TypeError("Cannot read private member from an object whose class did not declare it");
        return kind === "m" ? f : kind === "a" ? f.call(receiver) : f ? f.value : state.get(receiver);
    };

    __classPrivateFieldSet = function (receiver, state, value, kind, f) {
        if (kind === "m") throw new TypeError("Private method is not writable");
        if (kind === "a" && !f) throw new TypeError("Private accessor was defined without a setter");
        if (typeof state === "function" ? receiver !== state || !f : !state.has(receiver)) throw new TypeError("Cannot write private member to an object whose class did not declare it");
        return (kind === "a" ? f.call(receiver, value) : f ? f.value = value : state.set(receiver, value)), value;
    };

    exporter("__extends", __extends);
    exporter("__assign", __assign);
    exporter("__rest", __rest);
    exporter("__decorate", __decorate);
    exporter("__param", __param);
    exporter("__metadata", __metadata);
    exporter("__awaiter", __awaiter);
    exporter("__generator", __generator);
    exporter("__exportStar", __exportStar);
    exporter("__createBinding", __createBinding);
    exporter("__values", __values);
    exporter("__read", __read);
    exporter("__spread", __spread);
    exporter("__spreadArrays", __spreadArrays);
    exporter("__spreadArray", __spreadArray);
    exporter("__await", __await);
    exporter("__asyncGenerator", __asyncGenerator);
    exporter("__asyncDelegator", __asyncDelegator);
    exporter("__asyncValues", __asyncValues);
    exporter("__makeTemplateObject", __makeTemplateObject);
    exporter("__importStar", __importStar);
    exporter("__importDefault", __importDefault);
    exporter("__classPrivateFieldGet", __classPrivateFieldGet);
    exporter("__classPrivateFieldSet", __classPrivateFieldSet);
});
});

var service_worker = createCommonjsModule(function (module, exports) {
// Copyright (C) 2020 The Android Open Source Project
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
Object.defineProperty(exports, "__esModule", { value: true });

const LOG_TAG = `ServiceWorker: `;
const CACHE_NAME = 'ui-perfetto-dev';
// If the fetch() for the / doesn't respond within 3s, return a cached version.
// This is to avoid that a user waits too much if on a flaky network.
const INDEX_TIMEOUT_MS = 3000;
// Use more relaxed timeouts when caching the subresources for the new version
// in the background.
const INSTALL_TIMEOUT_MS = 30000;
// The install() event is fired:
// 1. On the first visit, when there is no SW installed.
// 2. Every time the user opens the site and the version has been updated (they
//    will get the newer version regardless, unless we hit INDEX_TIMEOUT_MS).
// The latter happens because:
// - / (index.html) is always served from the network (% timeout) and it pulls
//   /v1.2-sha/frontend_bundle.js.
// - /v1.2-sha/frontend_bundle.js will register /service_worker.js?v=v1.2-sha.
// The service_worker.js script itself never changes, but the browser
// re-installs it because the version in the V? query-string argument changes.
// The reinstallation will cache the new files from the v.1.2-sha/manifest.json.
self.addEventListener('install', event => {
    const doInstall = () => tslib.__awaiter(void 0, void 0, void 0, function* () {
        if (yield caches.has('BYPASS_SERVICE_WORKER')) {
            // Throw will prevent the installation.
            throw new Error(LOG_TAG + 'skipping installation, bypass enabled');
        }
        // Delete old cache entries from the pre-feb-2021 service worker.
        for (const key of yield caches.keys()) {
            if (key.startsWith('dist-')) {
                yield caches.delete(key);
            }
        }
        // The UI should register this as service_worker.js?v=v1.2-sha. Extract the
        // version number and pre-fetch all the contents for the version.
        const match = /\bv=([\w.-]*)/.exec(location.search);
        if (!match) {
            throw new Error('Failed to install. Was epecting a query string like ' +
                `?v=v1.2-sha query string, got "${location.search}" instead`);
        }
        yield installAppVersionIntoCache(match[1]);
        // skipWaiting() still waits for the install to be complete. Without this
        // call, the new version would be activated only when all tabs are closed.
        // Instead, we ask to activate it immediately. This is safe because the
        // subresources are versioned (e.g. /v1.2-sha/frontend_bundle.js). Even if
        // there is an old UI tab opened while we activate() a newer version, the
        // activate() would just cause cache-misses, hence fetch from the network,
        // for the old tab.
        self.skipWaiting();
    });
    event.waitUntil(doInstall());
});
self.addEventListener('activate', (event) => {
    console.info(LOG_TAG + 'activated');
    const doActivate = () => tslib.__awaiter(void 0, void 0, void 0, function* () {
        // This makes a difference only for the very first load, when no service
        // worker is present. In all the other cases the skipWaiting() will hot-swap
        // the active service worker anyways.
        yield self.clients.claim();
    });
    event.waitUntil(doActivate());
});
self.addEventListener('fetch', event => {
    // The early return here will cause the browser to fall back on standard
    // network-based fetch.
    if (!shouldHandleHttpRequest(event.request)) {
        console.debug(LOG_TAG + `serving ${event.request.url} from network`);
        return;
    }
    event.respondWith(handleHttpRequest(event.request));
});
function shouldHandleHttpRequest(req) {
    // Suppress warning: 'only-if-cached' can be set only with 'same-origin' mode.
    // This seems to be a chromium bug. An internal code search suggests this is a
    // socially acceptable workaround.
    if (req.cache === 'only-if-cached' && req.mode !== 'same-origin') {
        return false;
    }
    const url = new URL(req.url);
    if (url.pathname === '/live_reload')
        return false;
    return req.method === 'GET' && url.origin === self.location.origin;
}
function handleHttpRequest(req) {
    return tslib.__awaiter(this, void 0, void 0, function* () {
        if (!shouldHandleHttpRequest(req)) {
            throw new Error(LOG_TAG + `${req.url} shouldn't have been handled`);
        }
        // We serve from the cache even if req.cache == 'no-cache'. It's a bit
        // contra-intuitive but it's the most consistent option. If the user hits the
        // reload button*, the browser requests the "/" index with a 'no-cache' fetch.
        // However all the other resources (css, js, ...) are requested with a
        // 'default' fetch (this is just how Chrome works, it's not us). If we bypass
        // the service worker cache when we get a 'no-cache' request, we can end up in
        // an inconsistent state where the index.html is more recent than the other
        // resources, which is undesirable.
        // * Only Ctrl+R. Ctrl+Shift+R will always bypass service-worker for all the
        // requests (index.html and the rest) made in that tab.
        const cacheOps = { cacheName: CACHE_NAME };
        const url = new URL(req.url);
        if (url.pathname === '/') {
            try {
                console.debug(LOG_TAG + `Fetching live ${req.url}`);
                // The await bleow is needed to fall through in case of an exception.
                return yield fetchWithTimeout(req, INDEX_TIMEOUT_MS);
            }
            catch (err) {
                console.warn(LOG_TAG + `Failed to fetch ${req.url}, using cache.`, err);
                // Fall through the code below.
            }
        }
        else if (url.pathname === '/offline') {
            // Escape hatch to force serving the offline version without attemping the
            // network fetch.
            const cachedRes = yield caches.match(new Request('/'), cacheOps);
            if (cachedRes)
                return cachedRes;
        }
        const cachedRes = yield caches.match(req, cacheOps);
        if (cachedRes) {
            console.debug(LOG_TAG + `serving ${req.url} from cache`);
            return cachedRes;
        }
        // In any other case, just propagate the fetch on the network, which is the
        // safe behavior.
        console.warn(LOG_TAG + `cache miss on ${req.url}, using live network`);
        return fetch(req);
    });
}
function installAppVersionIntoCache(version) {
    return tslib.__awaiter(this, void 0, void 0, function* () {
        const manifestUrl = `${version}/manifest.json`;
        try {
            console.log(LOG_TAG + `Starting installation of ${manifestUrl}`);
            yield caches.delete(CACHE_NAME);
            const resp = yield fetchWithTimeout(manifestUrl, INSTALL_TIMEOUT_MS);
            const manifest = yield resp.json();
            const manifestResources = manifest['resources'];
            if (!manifestResources || !(manifestResources instanceof Object)) {
                throw new Error(`Invalid manifest ${manifestUrl} : ${manifest}`);
            }
            const cache = yield caches.open(CACHE_NAME);
            const urlsToCache = [];
            // We use cache:reload to make sure that the index is always current and we
            // don't end up in some cycle where we keep re-caching the index coming from
            // the service worker itself.
            urlsToCache.push(new Request('/', { cache: 'reload', mode: 'same-origin' }));
            for (const [resource, integrity] of Object.entries(manifestResources)) {
                // We use cache: no-cache rather then reload here because the versioned
                // sub-resources are expected to be immutable and should never be
                // ambiguous. A revalidation request is enough.
                const reqOpts = {
                    cache: 'no-cache',
                    mode: 'same-origin',
                    integrity: `${integrity}`
                };
                urlsToCache.push(new Request(`${version}/${resource}`, reqOpts));
            }
            yield cache.addAll(urlsToCache);
            console.log(LOG_TAG + 'installation completed for ' + version);
        }
        catch (err) {
            yield caches.delete(CACHE_NAME);
            console.error(LOG_TAG + `Installation failed for ${manifestUrl}`, err);
            throw err;
        }
    });
}
function fetchWithTimeout(req, timeoutMs) {
    const url = req.url || `${req}`;
    return new Promise((resolve, reject) => {
        const timerId = setTimeout(() => {
            reject(`Timed out while fetching ${url}`);
        }, timeoutMs);
        fetch(req).then(resp => {
            clearTimeout(timerId);
            if (resp.ok) {
                resolve(resp);
            }
            else {
                reject(`Fetch failed for ${url}: ${resp.status} ${resp.statusText}`);
            }
        }, reject);
    });
}

});

return service_worker;

}());
//# sourceMappingURL=service_worker.js.map
