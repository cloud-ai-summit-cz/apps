import { useEffect, useState } from 'react';
import { MsalProvider } from '@azure/msal-react';
import { BrowserRouter } from 'react-router-dom';
import { EventType } from '@azure/msal-browser';
import { msalInstance } from './config/authConfig';
import AppRoutes from './routes/AppRoutes';

function App() {
  const [isInitialized, setIsInitialized] = useState(false);

  useEffect(() => {
    const initializeMsal = async () => {
      try {
        // Initialize MSAL instance
        await msalInstance.initialize();
        
        // Handle redirect promise
        const response = await msalInstance.handleRedirectPromise();
        
        if (response) {
          console.log('Login successful:', response);
        }
        
        // Account selection logic
        const accounts = msalInstance.getAllAccounts();
        if (accounts.length > 0) {
          msalInstance.setActiveAccount(accounts[0]);
        }

        // Listen for login events
        msalInstance.addEventCallback((event) => {
          if (event.eventType === EventType.LOGIN_SUCCESS && event.payload) {
            const payload = event.payload as any;
            const account = payload.account;
            msalInstance.setActiveAccount(account);
          }
        });

        setIsInitialized(true);
      } catch (error) {
        console.error('MSAL initialization error:', error);
        setIsInitialized(true); // Still set to true to show error UI
      }
    };

    initializeMsal();
  }, []);

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Initializing...</p>
        </div>
      </div>
    );
  }

  return (
    <MsalProvider instance={msalInstance}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </MsalProvider>
  );
}

export default App;

