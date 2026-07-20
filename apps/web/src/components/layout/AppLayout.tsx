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
    <div className="relative flex h-screen overflow-hidden bg-background">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-40 h-[500px] w-[500px] rounded-full bg-primary/10 blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 h-[500px] w-[500px] rounded-full bg-secondary/10 blur-[120px]" />
        <div className="absolute left-1/3 top-1/2 h-[400px] w-[400px] rounded-full bg-accent/8 blur-[140px]" />
      </div>

      <div className="relative z-10 hidden md:block">
        <Sidebar collapsed={collapsed} onCollapse={toggleCollapsed} />
      </div>

      <div
        className={`fixed inset-0 z-40 md:hidden transition-opacity duration-300 ${
          mobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setMobileOpen(false)}
      >
        <div className="absolute inset-0 bg-background/70 backdrop-blur-md" />
        <div
          className={`absolute inset-y-0 left-0 w-72 shadow-2xl transition-transform duration-300 ${
            mobileOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <Sidebar onNavigate={() => setMobileOpen(false)} onCollapse={toggleCollapsed} />
        </div>
      </div>

      <div className="relative z-10 flex min-w-0 flex-1 flex-col overflow-hidden">
        <Topbar
          onToggleSidebar={() => {
            if (window.innerWidth < 768) setMobileOpen((p) => !p);
            else toggleCollapsed();
          }}
        />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto min-h-full w-full max-w-[1600px] p-4 md:p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
