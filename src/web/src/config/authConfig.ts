import { PublicClientApplication, Configuration, LogLevel } from '@azure/msal-browser';

const resolveRedirectUri = () => {
  const runtimeValue = window.ENV_CONFIG?.MSAL_REDIRECT_URI || import.meta.env.VITE_MSAL_REDIRECT_URI;
  if (runtimeValue && runtimeValue.trim().length > 0) {
    return runtimeValue;
  }
  return window.location?.origin || 'http://localhost:3000';
};

const redirectUri = resolveRedirectUri();

// MSAL configuration
const msalConfig: Configuration = {
  auth: {
    clientId: '5163cc2b-3d50-4278-8fbc-c13f3f0de588',
    authority: 'https://login.microsoftonline.com/6ce4f237-667f-43f5-aafd-cbef954adf97',
    redirectUri,
    postLogoutRedirectUri: redirectUri,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) {
          return;
        }
        switch (level) {
          case LogLevel.Error:
            console.error('[MSAL Error]', message);
            return;
          case LogLevel.Info:
            console.info('[MSAL Info]', message);
            return;
          case LogLevel.Verbose:
            console.debug('[MSAL Verbose]', message);
            return;
          case LogLevel.Warning:
            console.warn('[MSAL Warning]', message);
            return;
        }
      },
      logLevel: LogLevel.Verbose,
    },
  },
};

// Create MSAL instance
export const msalInstance = new PublicClientApplication(msalConfig);

// Login request configuration
export const loginRequest = {
  scopes: ['api://5163cc2b-3d50-4278-8fbc-c13f3f0de588/App.Access'],
};

// Token request for API calls
export const tokenRequest = {
  scopes: ['api://5163cc2b-3d50-4278-8fbc-c13f3f0de588/App.Access'],
};
