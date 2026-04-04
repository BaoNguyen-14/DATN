import { NavLink } from "react-router-dom";
import { clsx } from "clsx";

export default function Sidebar() {
  return (
    <aside className="hidden lg:flex flex-col h-screen w-20 fixed left-0 top-0 bg-slate-50 border-r border-slate-200 z-50 py-8 overflow-hidden items-center justify-between">
      <div className="flex flex-col items-center gap-8 w-full">
        <div className="text-lg font-black text-blue-900">SC</div>
        <nav className="flex flex-col w-full">
          <NavLink
            to="/"
            className={({ isActive }) =>
              clsx(
                "flex flex-col items-center justify-center gap-1 py-6 transition-all duration-200 ease-in-out hover:scale-105",
                isActive
                  ? "bg-blue-50 text-blue-800 border-r-4 border-blue-800"
                  : "text-slate-500 hover:bg-slate-100 hover:text-blue-700"
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className="material-symbols-outlined"
                  style={{ fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0" }}
                >
                  dashboard
                </span>
                <span className="font-headline text-[10px] uppercase tracking-widest font-bold">HOME</span>
              </>
            )}
          </NavLink>

          <NavLink
            to="/history"
            className={({ isActive }) =>
              clsx(
                "flex flex-col items-center justify-center gap-1 py-6 transition-all duration-200 ease-in-out hover:scale-105",
                isActive
                  ? "bg-blue-50 text-blue-800 border-r-4 border-blue-800"
                  : "text-slate-500 hover:bg-slate-100 hover:text-blue-700"
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className="material-symbols-outlined"
                  style={{ fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0" }}
                >
                  history
                </span>
                <span className="font-headline text-[10px] uppercase tracking-widest font-bold">HISTORY</span>
              </>
            )}
          </NavLink>

          <NavLink
            to="/settings"
            className={({ isActive }) =>
              clsx(
                "flex flex-col items-center justify-center gap-1 py-6 transition-all duration-200 ease-in-out hover:scale-105",
                isActive
                  ? "bg-blue-50 text-blue-800 border-r-4 border-blue-800"
                  : "text-slate-500 hover:bg-slate-100 hover:text-blue-700"
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className="material-symbols-outlined"
                  style={{ fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0" }}
                >
                  settings
                </span>
                <span className="font-headline text-[10px] uppercase tracking-widest font-bold">SETTINGS</span>
              </>
            )}
          </NavLink>
        </nav>
      </div>
      <div className="flex flex-col items-center gap-4">
        <button className="text-slate-400 hover:text-blue-900 transition-colors">
          <span className="material-symbols-outlined">support_agent</span>
        </button>
      </div>
    </aside>
  );
}