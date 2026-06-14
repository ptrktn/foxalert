// PWA Install Prompt for FoxAlert
let deferredPrompt;
let installPromptShown = false;

function createPWAPrompt() {
  if (document.getElementById('pwa-install-prompt')) {
    return;
  }

  const style = document.createElement('style');
  style.textContent = `
    #pwa-install-prompt {
      display: none;
      position: fixed;
      bottom: 20px;
      right: 20px;
      background: #2563eb;
      color: white;
      padding: 16px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
      z-index: 10000;
      max-width: 420px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      font-family: system-ui, -apple-system, 'Segoe UI', Roboto;
    }

    .pwa-prompt-header {
      font-size: 16px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .pwa-prompt-text {
      font-size: 14px;
      line-height: 1.4;
      opacity: 0.95;
    }

    .pwa-prompt-buttons {
      display: flex;
      gap: 8px;
      margin-top: 4px;
    }

    .pwa-prompt-buttons button {
      padding: 10px 16px;
      margin: 0;
      font-size: 13px;
      font-weight: 600;
      width: auto;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.2s;
    }

    .pwa-install-btn {
      background: white;
      color: #2563eb;
      flex: 1;
      min-width: 80px;
    }

    .pwa-install-btn:hover {
      background: #f0f0f0;
    }

    .pwa-install-btn:active {
      background: #e8e8e8;
    }

    .pwa-close-btn {
      background: rgba(255, 255, 255, 0.25);
      color: white;
      min-width: 44px;
    }

    .pwa-close-btn:hover {
      background: rgba(255, 255, 255, 0.35);
    }

    @media (max-width: 480px) {
      #pwa-install-prompt {
        left: 12px;
        right: 12px;
        max-width: none;
      }

      .pwa-prompt-buttons {
        width: 100%;
      }

      .pwa-install-btn {
        flex: 1;
      }
    }
  `;

  document.head.appendChild(style);

  const promptDiv = document.createElement('div');
  promptDiv.id = 'pwa-install-prompt';
  promptDiv.innerHTML = `
    <div class="pwa-prompt-header">
      📱 Install FoxAlert
    </div>
    <div class="pwa-prompt-text">
      Add to home screen for quick access and offline support
    </div>
    <div class="pwa-prompt-buttons">
      <button type="button" class="pwa-install-btn">Install Now</button>
      <button type="button" class="pwa-close-btn">✕</button>
    </div>
  `;

  document.body.appendChild(promptDiv);
  promptDiv.querySelector('.pwa-install-btn').addEventListener('click', installPWA);
  promptDiv.querySelector('.pwa-close-btn').addEventListener('click', closePWAPrompt);
}

function showInstallPrompt() {
  createPWAPrompt();
  const promptDiv = document.getElementById('pwa-install-prompt');
  if (promptDiv && !installPromptShown) {
    promptDiv.style.display = 'flex';
    installPromptShown = true;
    console.log('✓ Install prompt displayed');
  }
}

async function installPWA() {
  if (!deferredPrompt) {
    console.warn('⚠ deferredPrompt not available');
    alert('App installation is not available on this device/browser');
    return;
  }

  console.log('User triggered install');
  deferredPrompt.prompt();
  const { outcome } = await deferredPrompt.userChoice;
  console.log('User response to install prompt:', outcome);
  deferredPrompt = null;

  const promptDiv = document.getElementById('pwa-install-prompt');
  if (promptDiv) {
    promptDiv.style.display = 'none';
  }
}

function closePWAPrompt() {
  const promptDiv = document.getElementById('pwa-install-prompt');
  if (promptDiv) {
    promptDiv.style.display = 'none';
  }
}

window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault();
  deferredPrompt = event;
  console.log('✓ beforeinstallprompt event fired - app is installable');
  showInstallPrompt();
});

window.addEventListener('appinstalled', () => {
  console.log('✓ PWA was installed successfully');
  const promptDiv = document.getElementById('pwa-install-prompt');
  if (promptDiv) {
    promptDiv.style.display = 'none';
  }
});

window.addEventListener('load', () => {
  createPWAPrompt();

  const isPWA = window.matchMedia('(display-mode: standalone)').matches ||
                navigator.standalone === true ||
                document.referrer.includes('android-app://');

  if (isPWA) {
    console.log('✓ App is running as a PWA');
  }

  setTimeout(() => {
    if (!deferredPrompt && !isPWA) {
      console.log('ℹ Install prompt not available. Debug info:');
      console.log('  - Browser:', navigator.userAgent);
      console.log('  - Manifest valid:', document.querySelector('link[rel="manifest"]') ? '✓' : '✗');
      console.log('  - Service Worker registered:', 'serviceWorker' in navigator ? '✓' : '✗');
      console.log('  - Display mode:', window.matchMedia('(display-mode: standalone)').matches ? 'standalone' : 'browser');
      console.log('  - Platform:', navigator.platform);
      console.log('');
      console.log('For Linux Chrome: Install prompt appears after multiple visits');
      console.log('or use: Menu → More tools → Create shortcut');
    }
  }, 2000);
});
