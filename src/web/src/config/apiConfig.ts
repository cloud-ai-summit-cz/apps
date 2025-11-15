// Extend Window interface to include ENV_CONFIG
declare global {
  interface Window {
    ENV_CONFIG?: {
      TOY_SERVICE_URL?: string;
      TRIP_SERVICE_URL?: string;
      MSAL_REDIRECT_URI?: string;
    };
  }
}

// Runtime configuration loaded from env-config.js (set at container start) or build-time env vars
export const API_CONFIG = {
  TOY_SERVICE_BASE_URL: window.ENV_CONFIG?.TOY_SERVICE_URL || import.meta.env.VITE_TOY_SERVICE_URL || 'http://localhost:8001',
  TRIP_SERVICE_BASE_URL: window.ENV_CONFIG?.TRIP_SERVICE_URL || import.meta.env.VITE_TRIP_SERVICE_URL || 'http://localhost:8002',
  MSAL_REDIRECT_URI: window.ENV_CONFIG?.MSAL_REDIRECT_URI || import.meta.env.VITE_MSAL_REDIRECT_URI || 'http://localhost:3000',
};
