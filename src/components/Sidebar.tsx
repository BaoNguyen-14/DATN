import { NavLink } from "react-router-dom";
import { clsx } from "clsx";

const navItems = [
  { to: "/", icon: "dashboard", label: "HOME" },
  { to: "/parking-map", icon: "local_parking", label: "PARKING" },
  { to: "/history", icon: "history", label: "HISTORY" },
  { to: "/settings", icon: "settings", label: "SETTINGS" },
];

export default function Sidebar() {
  return (
    <aside className="hidden lg:flex flex-col h-screen w-20 fixed left-0 top-0 bg-slate-50 border-r border-slate-200 z-50 py-8 overflow-hidden items-center justify-between">
      <div className="flex flex-col items-center gap-8 w-full">
        <div className="w-12 h-12 flex items-center justify-center mt-2 hover:scale-105 transition-transform cursor-pointer">
          <img src="/logo.png" alt="BK Logo" className="w-full h-full object-contain drop-shadow-sm" />
        </div>
        <nav className="flex flex-col w-full">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                clsx(
                  "flex flex-col items-center justify-center gap-1 py-5 transition-all duration-200 ease-in-out hover:scale-105",
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
                    {item.icon}
                  </span>
                  <span className="font-headline text-[9px] uppercase tracking-widest font-bold">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </aside>
  );
}