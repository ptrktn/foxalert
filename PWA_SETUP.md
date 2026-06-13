# PWA Setup Guide for FoxAlert

This document describes the Progressive Web App (PWA) components added to the FoxAlert application.

## Components Added

### 1. **Web App Manifest** (`/static/manifest.json`)
- Defines app metadata, name, icons, display mode, and theme colors
- Enables "Add to Home Screen" functionality on Android and iOS
- Specifies standalone display mode for full-screen experience
- Includes app shortcuts for quick access

### 2. **Service Worker** (`/static/service-worker.js`)
- Enables offline functionality with intelligent caching strategies
- **Cache-First**: Static assets (CSS, JS, images)
- **Network-First**: API and auth routes (login, register)
- Handles background synchronization and push notifications (ready for implementation)

### 3. **PWA Install Prompt** (`/static/pwa-install.js`)
- Shows install banner on supported browsers/devices
- Handles `beforeinstallprompt` event
- Detects if app is running in standalone mode
- Styled install button in bottom-right corner

### 4. **Updated Base Template** (`/templates/base.html`)
- Links manifest.json
- Registers service worker on page load
- Includes theme color and icons meta tags
- Loads PWA install prompt script

### 5. **Offline Fallback** (`/templates/offline.html`)
- Displayed when user is offline and content is not cached

## Features Enabled

✅ **Installable** - Add to home screen on Android/iOS/Desktop
✅ **Offline Support** - Cached content available without internet
✅ **App-like Experience** - Runs in standalone mode (no browser chrome)
✅ **Responsive Design** - Works on all screen sizes
✅ **Update Detection** - Checks for service worker updates every 60 seconds
✅ **Security Focus** - Network-first for sensitive auth routes

## Icon Setup (Optional)

The manifest references icons at:
- `/static/icons/icon-192.png` (192x192)
- `/static/icons/icon-512.png` (512x512)
- `/static/icons/icon-maskable-192.png` (192x192, maskable)
- `/static/icons/icon-maskable-512.png` (512x512, maskable)

**To generate icons:**

```bash
# Create icons directory
mkdir -p static/icons

# Use ImageMagick or online tools to convert logo to PNG
# https://www.favicon-generator.org/
# https://www.imagemagick.org/
```

For now, the app will use SVG favicons embedded in the HTML. Replace with real PNG files for production.

## Testing PWA

### Chrome DevTools
1. Open DevTools (F12)
2. Go to **Application** tab
3. Check **Manifest** section for validity
4. Check **Service Workers** section for registration
5. Simulate offline mode: Network tab → Offline checkbox
6. Go to **Lighthouse** and run PWA audit

### Installation
1. On supported browser (Chrome, Edge, Opera), app menu should show "Install app" option
2. Or click the install prompt button
3. Once installed, launch from home screen or app menu

### Offline Testing
1. Install the PWA
2. Open DevTools → Network → check "Offline"
3. Navigate app - cached pages should load
4. Auth routes will show offline error (as designed for security)

## Customization

### Change App Name
Edit `manifest.json`:
```json
{
  "name": "Your App Name",
  "short_name": "Your Short Name"
}
```

### Disable Install Prompt
Remove this line from `base.html`:
```html
<script src="{{ url_for('static', filename='pwa-install.js') }}"></script>
```

### Adjust Cache Strategy
Edit `service-worker.js` and modify `CACHE_FIRST_ROUTES` or `NETWORK_FIRST_ROUTES` arrays.

### Add Push Notifications
Implement in service worker with Web Push API:
```javascript
self.addEventListener('push', event => {
  const data = event.data.json();
  self.registration.showNotification(data.title, {
    body: data.body,
    icon: '/static/icons/icon-192.png'
  });
});
```

## Production Checklist

- [ ] Replace SVG favicons with actual PNG icons (192x192, 512x512)
- [ ] Test on multiple devices and browsers
- [ ] Verify HTTPS is enabled (required for PWA)
- [ ] Update manifest colors and metadata
- [ ] Test offline scenarios
- [ ] Set up icon maskable versions for adaptive icons
- [ ] Monitor service worker updates
- [ ] Add push notification support (optional)
