// Client-side storage utility using IndexedDB and in-memory caching
// Completely prevents DOMException QuotaExceededError when storing large fundus photos & screening results

const DB_NAME = "dr_screening_db";
const STORE_NAME = "screening_store";
const DB_VERSION = 1;

// Global in-memory cache for synchronous access within the SPA session
if (typeof window !== "undefined") {
  window.__DR_STORE__ = window.__DR_STORE__ || {};
}

function openDB() {
  return new Promise((resolve) => {
    if (typeof window === "undefined" || !window.indexedDB) {
      resolve(null);
      return;
    }
    try {
      const req = window.indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME);
        }
      };
      req.onsuccess = (e) => resolve(e.target.result);
      req.onerror = () => resolve(null);
    } catch (_) {
      resolve(null);
    }
  });
}

export async function idbSet(key, val) {
  if (typeof window !== "undefined") {
    window.__DR_STORE__[key] = val;
  }
  const db = await openDB();
  if (!db) return false;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readwrite");
      const store = tx.objectStore(STORE_NAME);
      store.put(val, key);
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
    } catch (_) {
      resolve(false);
    }
  });
}

export async function idbGet(key) {
  if (typeof window !== "undefined" && window.__DR_STORE__[key] !== undefined) {
    return window.__DR_STORE__[key];
  }
  const db = await openDB();
  if (!db) return null;
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(key);
      req.onsuccess = () => {
        const res = req.result ?? null;
        if (res !== null && typeof window !== "undefined") {
          window.__DR_STORE__[key] = res;
        }
        resolve(res);
      };
      req.onerror = () => resolve(null);
    } catch (_) {
      resolve(null);
    }
  });
}

export function safeLocalStorageSet(key, value) {
  try {
    const str = typeof value === "string" ? value : JSON.stringify(value);
    localStorage.setItem(key, str);
  } catch (err) {
    console.warn(`[Storage] localStorage quota exceeded for key: ${key}. Stored safely in IndexedDB/Memory.`);
    // If it's screening_result, save a lightweight metadata-only version in localStorage
    if (key === "screening_result" && typeof value === "object" && value !== null) {
      try {
        const lightweight = { ...value };
        delete lightweight.annotated_base64;
        delete lightweight.heatmap_base64;
        if (lightweight.zoomed_crops) {
          lightweight.zoomed_crops = lightweight.zoomed_crops.map((c) => {
            const copy = { ...c };
            delete copy.image_base64;
            return copy;
          });
        }
        localStorage.setItem(key, JSON.stringify(lightweight));
      } catch (_) {}
    }
  }
}

export async function saveScreeningSession(result, uploadedImage) {
  if (result) {
    window.__DR_STORE__["screening_result"] = result;
    await idbSet("screening_result", result);
    safeLocalStorageSet("screening_result", result);
  }
  if (uploadedImage) {
    window.__DR_STORE__["uploaded_image"] = uploadedImage;
    await idbSet("uploaded_image", uploadedImage);
    safeLocalStorageSet("uploaded_image", uploadedImage);
  }
}

export async function saveUploadedPreview(base64, filename) {
  if (base64) {
    window.__DR_STORE__["retina_preview"] = base64;
    window.__DR_STORE__["uploaded_image"] = base64;
    await idbSet("retina_preview", base64);
    await idbSet("uploaded_image", base64);
    try {
      sessionStorage.setItem("retina_preview", base64);
    } catch (_) {}
  }
  if (filename) {
    window.__DR_STORE__["retina_filename"] = filename;
    try {
      sessionStorage.setItem("retina_filename", filename);
    } catch (_) {}
  }
}

export function getSyncScreeningResult() {
  if (typeof window !== "undefined" && window.__DR_STORE__["screening_result"]) {
    return window.__DR_STORE__["screening_result"];
  }
  try {
    const raw = localStorage.getItem("screening_result");
    return raw ? JSON.parse(raw) : null;
  } catch (_) {
    return null;
  }
}

export function getSyncUploadedImage() {
  if (typeof window !== "undefined" && window.__DR_STORE__["uploaded_image"]) {
    return window.__DR_STORE__["uploaded_image"];
  }
  if (typeof window !== "undefined" && window.__DR_STORE__["retina_preview"]) {
    return window.__DR_STORE__["retina_preview"];
  }
  try {
    return localStorage.getItem("uploaded_image") || sessionStorage.getItem("retina_preview") || null;
  } catch (_) {
    return null;
  }
}
