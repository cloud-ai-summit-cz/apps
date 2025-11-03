import { useIsAuthenticated, useMsal } from '@azure/msal-react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { loginRequest } from '../config/authConfig';
import Layout from '../components/Layout';
import ToyCatalog from '../pages/ToyCatalog';
import ToyDetail from '../pages/ToyDetail';

function AppRoutes() {
  const isAuthenticated = useIsAuthenticated();
  const { instance } = useMsal();

  // If not authenticated, show login page
  if (!isAuthenticated) {
    const handleLogin = () => {
      instance.loginRedirect(loginRequest).catch(error => {
        console.error('Login error:', error);
      });
    };

    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="mb-6">
              <div className="w-16 h-16 bg-gray-900 rounded-xl mx-auto flex items-center justify-center">
                <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">ToyTrips</h1>
            <p className="text-gray-600 mb-8">Sign in to manage your toy adventures</p>
            <button
              onClick={handleLogin}
              className="w-full bg-gray-900 hover:bg-gray-800 text-white font-medium py-3 px-6 rounded-lg transition-colors duration-200"
            >
              Sign in with Microsoft
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<ToyCatalog />} />
        <Route path="toy/:id" element={<ToyDetail />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default AppRoutes;
