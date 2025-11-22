import 'zone.js'; // Import zone.js before anything else to enable async context propagation
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initializeTelemetry, shutdownTelemetry } from './config/telemetryConfig'

// Initialize OpenTelemetry as early as possible
// This ensures all subsequent operations are traced
console.log('[App] Starting telemetry initialization...');
initializeTelemetry().then(() => {
  console.log('[App] Telemetry initialization complete');
}).catch((error) => {
  console.error('[App] Telemetry initialization failed:', error);
});

// Register cleanup handler to flush telemetry on page unload
window.addEventListener('beforeunload', () => {
  shutdownTelemetry().catch(console.error);
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
