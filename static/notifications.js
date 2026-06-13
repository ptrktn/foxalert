// Client-side SSE notification handler
(function(){
  const statusLog = msg => console.log('[notif]', msg);

  function showInPageToast(title, body) {
    // Simple toast: console + tiny floating element
    const id = 'sse-toast';
    let el = document.getElementById(id);
    if (!el) {
      el = document.createElement('div');
      el.id = id;
      el.style.position = 'fixed';
      el.style.right = '20px';
      el.style.bottom = '80px';
      el.style.maxWidth = '320px';
      el.style.zIndex = 10001;
      document.body.appendChild(el);
    }
    const item = document.createElement('div');
    item.style.background = 'white';
    item.style.color = '#111';
    item.style.padding = '12px';
    item.style.marginTop = '8px';
    item.style.borderRadius = '8px';
    item.style.boxShadow = '0 6px 18px rgba(0,0,0,0.08)';
    item.innerHTML = `<strong>${title}</strong><div style="opacity:0.9;margin-top:6px">${body}</div>`;
    el.appendChild(item);
    setTimeout(() => item.remove(), 8000);
  }

  // Request notification permission when user clicks the enable button
  async function setupEnableButton() {
    const btn = document.getElementById('notify-enable-btn');
    if (!btn) return;
    btn.style.display = 'inline-block';
    btn.addEventListener('click', async () => {
      try {
        const perm = await Notification.requestPermission();
        statusLog('Notification permission: ' + perm);
        if (perm === 'granted') {
          try {
            const sub = await subscribeForPush();
            statusLog('Push subscription successful', sub);
          } catch (err) {
            console.warn('Push subscription failed', err);
          }
        }
        btn.style.display = 'none';
      } catch (e) {
        console.error(e);
      }
    });
  }

  // Convert base64 url string to Uint8Array for applicationServerKey
  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  async function subscribeForPush() {
    if (!('serviceWorker' in navigator)) throw new Error('No service worker');
    if (!('PushManager' in window)) throw new Error('Push not supported');

    const reg = await navigator.serviceWorker.ready;
    const res = await fetch('/vapid_public_key');
    if (!res.ok) throw new Error('Failed to get VAPID key');
    const body = await res.json();
    const publicKey = body.publicKey;
    if (!publicKey) throw new Error('VAPID public key not configured');

    const sub = await reg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(publicKey)
    });

    statusLog('Push subscription object created:', sub);

    // Send subscription to server
    const subscribeRes = await fetch('/push/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(sub)
    });
    const subscribeBody = await subscribeRes.text();
    statusLog('Push subscribe response', subscribeRes.status, subscribeBody);
    if (!subscribeRes.ok) {
      throw new Error('Subscription registration failed: ' + subscribeRes.status + ' ' + subscribeBody);
    }
    statusLog('Subscription registered with server:', subscribeBody);
    return sub;
  }

  function connectSSE() {
    if (!window.EventSource) {
      statusLog('EventSource not supported');
      return;
    }
    const es = new EventSource('/notifications/stream');
    es.onopen = () => statusLog('SSE connected');
    es.onerror = e => statusLog('SSE error: ' + e);
    es.onmessage = async (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'notification') {
          // Attempt native notification if permission granted
          if (window.Notification && Notification.permission === 'granted') {
            navigator.serviceWorker && navigator.serviceWorker.controller
              ? navigator.serviceWorker.getRegistration().then(reg => {
                  if (reg) {
                    reg.showNotification(msg.title, {
                      body: msg.body,
                      data: msg.data || {},
                      icon: '/static/icons/icon-192.png'
                    });
                  } else {
                    new Notification(msg.title, { body: msg.body, icon: '/static/icons/icon-192.png' });
                  }
                })
              : new Notification(msg.title, { body: msg.body, icon: '/static/icons/icon-192.png' });
          } else {
            // Fallback to in-page toast
            showInPageToast(msg.title || 'Notification', msg.body || '');
          }
        }
      } catch (err) {
        console.error('Failed to handle SSE message', err);
      }
    };
  }

  // Init on load
  window.addEventListener('load', () => {
    setupEnableButton();
    connectSSE();
  });
})();
