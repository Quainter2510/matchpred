import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../store/auth";

// «Соревнования» ведёт на "/" — корневой redirect открывает последнее
// посещённое соревнование (или хаб, если выбора нет).
const nav = [
  { to: "/", label: "Соревнования", icon: "🏆" },
  { to: "/profile", label: "Профиль", icon: "👤" },
];

export default function Sidebar() {
  const { user, isAdmin, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [menu, setMenu] = useState(false);

  // Аноним в лобби видит только «Соревнования» и кнопку «Войти».
  // Пункт «Админ» виден всегда (для админов) — в том числе суперадмину в
  // режиме игрока: там живёт чекбокс включения полных прав.
  const items = user ? [...nav] : [nav[0]];
  if (user && isAdmin()) items.push({ to: "/admin", label: "Админ", icon: "⚙️" });

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const active = (to: string) =>
    to === "/"
      ? // Пункт «Соревнования» активен и на хабе, и внутри комнаты.
        location.pathname === "/" || location.pathname.startsWith("/room")
      : location.pathname.startsWith(to);

  return (
    <>
      {/* Desktop sidebar */}
      <aside className="fixed left-0 top-0 hidden h-screen w-60 flex-col border-r border-slate-200 bg-white p-4 md:flex">
        <div className="mb-6 text-lg font-bold">⚽ ЧМ-2026</div>
        <nav className="flex flex-1 flex-col gap-1">
          {items.map((i) => (
            <Link
              key={i.to}
              to={i.to}
              className={`rounded-lg px-3 py-2 ${
                active(i.to) ? "bg-brand text-white" : "hover:bg-slate-100"
              }`}
            >
              <span className="mr-2">{i.icon}</span>
              {i.label}
            </Link>
          ))}
        </nav>
        {!user ? (
          <Link to="/login" className="btn-primary block w-full text-center">
            Войти
          </Link>
        ) : (
        <div className="relative">
          <button
            onClick={() => setMenu((m) => !m)}
            className="flex w-full items-center gap-2 rounded-lg p-2 hover:bg-slate-100"
          >
            {user?.avatar_url ? (
              <img src={user.avatar_url} className="h-8 w-8 rounded-full" />
            ) : (
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-300">
                {user?.nickname?.[0]?.toUpperCase()}
              </div>
            )}
            <span className="truncate">{user?.nickname}</span>
          </button>
          {menu && (
            <div className="absolute bottom-12 left-0 w-full rounded-lg border bg-white p-1 shadow">
              <Link
                to="/profile"
                className="block rounded px-3 py-2 hover:bg-slate-100"
                onClick={() => setMenu(false)}
              >
                Профиль
              </Link>
              <button
                onClick={handleLogout}
                className="block w-full rounded px-3 py-2 text-left text-red-600 hover:bg-slate-100"
              >
                Выход
              </button>
            </div>
          )}
        </div>
        )}
      </aside>

      {/* Mobile bottom bar */}
      <nav className="fixed bottom-0 left-0 z-10 flex w-full justify-around border-t border-slate-200 bg-white py-2 md:hidden">
        {items.map((i) => (
          <Link
            key={i.to}
            to={i.to}
            className={`flex flex-col items-center text-xs ${
              active(i.to) ? "text-brand" : "text-slate-500"
            }`}
          >
            <span className="text-lg">{i.icon}</span>
            {i.label}
          </Link>
        ))}
        {user ? (
          <button
            onClick={handleLogout}
            className="flex flex-col items-center text-xs text-slate-500"
          >
            <span className="text-lg">🚪</span>
            Выход
          </button>
        ) : (
          <Link
            to="/login"
            className="flex flex-col items-center text-xs text-brand"
          >
            <span className="text-lg">🔑</span>
            Войти
          </Link>
        )}
      </nav>
    </>
  );
}
