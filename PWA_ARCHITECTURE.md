# PWA Architecture Overview

## Project Structure After PWA Setup

```
foxalert/
├── app.py                          # Flask app (unchanged)
├── requirements.txt                # Python deps (unchanged)
├── Makefile                        # Build scripts (unchanged)
├── README.md                       # Project readme
│
├── static/                         # NEW: Static files (PWA core)
│   ├── manifest.json              # App metadata & icons manifest
│   ├── service-worker.js          # Offline caching & sync
│   ├── pwa-install.js             # Install prompt & detection
│   └── icons/                     # (Optional) App icons directory
│       ├── icon-192.png
│       ├── icon-512.png
│       ├── icon-maskable-192.png
│       └── icon-maskable-512.png
│
├── templates/
│   ├── base.html                  # UPDATED: PWA links & SW registration
│   ├── login.html                 # Login page (unchanged)
│   ├── index.html                 # Home page (unchanged)
│   ├── mfa_verify.html            # MFA verification (unchanged)
│   ├── mfa_setup.html             # MFA setup (unchanged)
│   └── offline.html               # NEW: Offline fallback page
│
├── PWA_SETUP.md                   # NEW: Detailed PWA guide
├── PWA_IMPLEMENTATION.md          # NEW: Implementation checklist
└── PWA_ARCHITECTURE.md            # NEW: This file
```

## PWA Component Flow

```
┌─────────────────────────────────────────────────────────┐
│              Browser / Mobile Device                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────────────────────────────┐       │
│  │         User visits foxalert.com             │       │
│  └────────────────────┬─────────────────────────┘       │
│                       │                                  │
│        ┌──────────────▼──────────────┐                  │
│        │   base.html loads           │                  │
│        │   - Manifest link           │                  │
│        │   - Theme colors            │                  │
│        │   - Favicon (SVG)           │                  │
│        └──────────────┬───────────────┘                  │
│                       │                                  │
│     ┌─────────────────▼─────────────────┐               │
│     │  Browser shows install prompt     │               │
│     │  (pwa-install.js logic)          │               │
│     │  - "Install FoxAlert" button     │               │
│     │  - Checks beforeinstallprompt    │               │
│     └──────────────┬──────────────────┘                 │
│                    │                                    │
│  ┌─────────────────▼────────────────────┐              │
│  │  Service Worker registers            │              │
│  │  (service-worker.js)                 │              │
│  │  - Cache app shell                   │              │
│  │  - Intercept fetch requests          │              │
│  │  - Handle offline scenarios          │              │
│  └──────────────┬─────────────────────┘               │
│                 │                                      │
│  ┌──────────────▼──────────────────┐                 │
│  │  App is now installable!        │                 │
│  │  - Add to home screen (Android) │                 │
│  │  - Install app (Desktop)        │                 │
│  │  - Add to home screen (iOS)     │                 │
│  └─────────────────────────────────┘                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## Service Worker Caching Strategy

```
┌────────────────────────────────────────────────────────┐
│            Incoming Fetch Request                      │
└────────────────────┬─────────────────────────────────┘
                     │
        ┌────────────▼──────────────┐
        │  Check URL path           │
        └────────────┬──────────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
    ▼                ▼                ▼
┌─────────────┐ ┌─────────────┐ ┌──────────────┐
│/static/*    │ │/login,      │ │ Other        │
│             │ │/register,   │ │ routes       │
│CACHE-FIRST  │ │/            │ │              │
│             │ │             │ │NETWORK-FIRST │
│1. Check     │ │NETWORK-FIRST│ │              │
│   cache     │ │             │ │1. Try fetch  │
│2. If found  │ │1. Try fetch │ │2. Cache if   │
│   return    │ │2. Cache if  │ │   success    │
│3. If not,   │ │   success   │ │3. Fall back  │
│   fetch &   │ │3. Fall back │ │   to cache   │
│   cache     │ │   to cache  │ │4. Offline    │
│4. Offline   │ │4. Offline   │ │   error      │
│   no cache  │ │   error     │ │              │
└─────────────┘ └─────────────┘ └──────────────┘
```

## Data Flow: Online vs Offline

### Online Mode
```
User Request → Service Worker → Network
     │                │            │
     └────────────────┼────────────┘
                      │
                Cache Update
                      │
                   Response
                      │
                   To User
```

### Offline Mode
```
User Request → Service Worker → Network ✗
     │                │
     └─────────────────┤
                       │
                  Check Cache
                       │
        ┌──────────────┴──────────────┐
        │                             │
     Found                         Not Found
        │                             │
    Cached Response            Offline Response
        │                             │
     To User                   Error Message
```

## Key PWA Files & Responsibilities

### `/static/manifest.json`
- **Purpose**: Browser app metadata
- **Provides**: App name, icons, colors, display mode
- **Used by**: Browser installation UI, app metadata display
- **Format**: JSON Web App Manifest spec

### `/static/service-worker.js`
- **Purpose**: Offline support & intelligent caching
- **Provides**: Install, activate, fetch event handlers
- **Manages**: Cache versioning, route-based strategies
- **Format**: JavaScript Service Worker API

### `/static/pwa-install.js`
- **Purpose**: User install prompts & PWA detection
- **Provides**: Install banner, event listeners
- **Handles**: beforeinstallprompt, appinstalled events
- **Displays**: Bottom-right install prompt (optional)

### `/templates/offline.html`
- **Purpose**: User-friendly offline fallback
- **Shown**: When cached content unavailable offline
- **Format**: HTML template with Flask/Jinja2

### `/templates/base.html` (Updated)
- **New additions**:
  - `<link rel="manifest">` - Points to manifest.json
  - `<meta name="theme-color">` - Sets title bar color
  - Meta description tag
  - Favicon and apple-touch-icon
  - Service worker registration script
  - PWA install prompt script include

## Update Cycle

```
┌─────────────────────────────────────────┐
│  App loads, SW registers               │
│  Cache version: v1                      │
└────────────────────┬────────────────────┘
                     │
        ┌────────────▼────────────┐
        │ Every 60 seconds:       │
        │ Check for updates       │
        │ (reg.update())          │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │ New version detected?   │
        │                         │
        └────┬──────────────┬─────┘
             │              │
          Yes              No
             │              │
             ▼              ▼
        ├─────────┐    ┌─────────┐
        │Download │    │Continue │
        │new      │    │using    │
        │service  │    │cache v1 │
        │worker   │    └─────────┘
        │(cache   │
        │v2)      │
        ├─────────┤
        │On next  │
        │page     │
        │reload:  │
        │Activate │
        │v2       │
        └─────────┘
```

## Installation Flow (Android Chrome)

```
1. User visits app
   ↓
2. beforeinstallprompt fires
   ↓
3. Install prompt appears
   ↓
4. User clicks "Install"
   ↓
5. Browser shows system dialog
   ↓
6. User confirms
   ↓
7. App added to home screen
   ↓
8. appinstalled event fires
   ↓
9. App launches in standalone mode
   (no browser chrome/URL bar)
```

## Security Model

```
┌─────────────────────────────────────┐
│  Authentication Routes              │
│  (/login, /register, /)             │
│                                     │
│  Strategy: NETWORK-FIRST            │
│  - Always try server first          │
│  - Only cache successful response   │
│  - Show error if offline            │
│  - Never auto-login from cache      │
│                                     │
│  WHY: Prevent stale auth data       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Static Assets                      │
│  (/static/css, /static/js, etc)     │
│                                     │
│  Strategy: CACHE-FIRST              │
│  - Serve from cache                 │
│  - Update cache in background       │
│  - Works offline immediately        │
│  - Updated on new SW deployment     │
│                                     │
│  WHY: Better performance            │
└─────────────────────────────────────┘
```

## Testing Scenarios

### Scenario 1: First Visit
- Service worker installed
- App shell cached
- Install prompt shown
- User can browse (online)

### Scenario 2: Return Visit Online
- Service worker activated
- Static assets served from cache
- API requests go to network
- App updates in background

### Scenario 3: Return Visit Offline
- Service worker serves cached content
- Network requests fail → fallback to cache
- Auth routes show offline error
- Static content loads normally

### Scenario 4: Installation
- User installs from browser
- App appears on home screen
- Launches in standalone mode
- Works like native app

## Browser Support

```
✅ Chrome 51+          - Full support
✅ Edge 17+            - Full support  
✅ Firefox 44+         - Full support (experimental)
✅ Opera 38+           - Full support
⚠️ Safari 16.4+        - Partial (install limitations)
✅ Android browsers    - Full support
✅ iOS Safari 16.4+    - Partial (add to home screen)
```
