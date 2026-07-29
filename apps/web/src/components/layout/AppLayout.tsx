import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('sidebar-collapsed') === 'true');
  const [mobileOpen, setMobileOpen] = useState(false);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('sidebar-collapsed', String(next));
      return next;
    });
  };

  return (
    <div className="flex min-h-[100dvh] overflow-hidden bg-background text-foreground">
      <div className="relative z-20 hidden shrink-0 border-r border-divider md:block">
        <Sidebar collapsed={collapsed} onNavigate={() => setMobileOpen(false)} />
      </div>

      <div
        className={`fixed inset-0 z-40 md:hidden ${
          mobileOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
        } transition-opacity duration-200`}
        aria-hidden={!mobileOpen}
        onClick={() => setMobileOpen(false)}
      >
        <div className="absolute inset-0 bg-black/70" />
        <div
          className={`absolute inset-y-0 left-0 w-[min(20rem,88vw)] border-r border-divider bg-sidebar shadow-elevated transition-transform duration-200 ${
            mobileOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
          onClick={(event) => event.stopPropagation()}
        >
          <Sidebar onNavigate={() => setMobileOpen(false)} />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Topbar
          collapsed={collapsed}
          onToggleCollapse={toggleCollapsed}
          onOpenMobileMenu={() => setMobileOpen(true)}
        />
        <main className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto min-h-full w-full max-w-[1680px] px-4 py-5 md:px-6 md:py-7 xl:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
