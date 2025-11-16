import { Outlet } from 'react-router-dom';
import { useMsal } from '@azure/msal-react';
import DemoDataPanel from './admin/DemoDataPanel';

function hasAdminRole(idTokenClaims?: Record<string, any>): boolean {
  const roles = idTokenClaims?.roles;
  if (!roles) return false;
  return Array.isArray(roles) ? roles.includes('Admin.FullAccess') : roles === 'Admin.FullAccess';
}

function Layout() {
  const { instance, accounts } = useMsal();

  const handleLogout = () => {
    instance.logoutRedirect();
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-xl font-semibold text-gray-900">Toy Service</h1>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                {accounts[0]?.name || accounts[0]?.username}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>
        {accounts[0] && hasAdminRole(accounts[0].idTokenClaims) && (
          <DemoDataPanel />
        )}
        <Outlet />
      </main>
    </div>
  );
}

export default Layout;
