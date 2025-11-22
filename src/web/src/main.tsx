import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initializeTelemetry, shutdownTelemetry } from './config/telemetryConfig'

// Initialize OpenTelemetry as early as possible
// This ensures all subsequent operations are traced
initializeTelemetry();

// Register cleanup handler to flush telemetry on page unload
window.addEventListener('beforeunload', () => {
  shutdownTelemetry().catch(console.error);
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
