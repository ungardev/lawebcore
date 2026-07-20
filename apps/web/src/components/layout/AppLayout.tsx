import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('sidebar-collapsed') === 'true';
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('sidebar-collapsed', String(next));
      return next;
    });
  };

  return (
    <div className="flex h-screen bg-background relative overflow-hidden">
      {/* Aurora background blobs */}
      <div
        className="fixed inset-0 z-0 pointer-events-none"
        aria-hidden="true"
      >
        <div className="absolute top-0 left-1/4 w-[600px] h-[600px] rounded-full bg-brand-pink/10 blur-[120px] animate-pulse" />
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] rounded-full bg-brand-purple/10 blur-[100px] animate-pulse" />
        <div className="absolute top-1/3 right-0 w-[400px] h-[400px] rounded-full bg-brand-blue/8 blur-[80px] animate-pulse" />
      </div>

      <div className="relative z-10 hidden md:block">
        <Sidebar collapsed={collapsed} />
      </div>

      <div
        className={`fixed inset-0 z-40 md:hidden transition-opacity duration-300 ${
          mobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setMobileOpen(false)}
      >
        <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
        <div
          className={`absolute inset-y-0 left-0 w-72 transition-transform duration-300 ${
            mobileOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <Sidebar onNavigate={() => setMobileOpen(false)} />
        </div>
      </div>

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden relative z-10">
        <Topbar
          onToggleSidebar={() => {
            if (window.innerWidth < 768) {
              setMobileOpen((p) => !p);
            } else {
              toggleCollapsed();
            }
          }}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 min-w-0 relative">
          <div className="absolute inset-0 bg-aurora opacity-60 pointer-events-none" />
          <div className="relative z-10">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
