import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { api, Room } from "../api/endpoints";
import { useAuth } from "../store/auth";
import AuthModal from "../components/AuthModal";

function RoomRow({ room, onOpen }: { room: Room; onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="flex w-full items-center justify-between rounded-lg border p-3 text-left hover:bg-slate-50"
    >
      <div>
        <div className="font-medium">{room.name}</div>
        <div className="text-xs text-slate-500">
          {room.member_count} участников
          {room.my_role === "admin" && " · вы админ"}
        </div>
      </div>
      <span className="text-brand">Открыть →</span>
    </button>
  );
}

function JoinCard({
  room,
  onJoined,
  onRequireAuth,
}: {
  room: Room;
  onJoined: () => void;
  onRequireAuth: () => boolean; // true = пользователь не авторизован, действие прервано
}) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const superadmin = useAuth((s) => s.isSuperadmin());
  const join = useMutation({
    mutationFn: () => api.joinRoom(room.id, password),
    onSuccess: onJoined,
    onError: (e: any) =>
      setError(e.response?.data?.detail || "Неверный пароль"),
  });
  return (
    <div className="rounded-lg border p-3">
      <div className="mb-2 flex items-center justify-between">
        <div className="font-medium">{room.name}</div>
        <span className="text-xs text-slate-500">{room.member_count} уч.</span>
      </div>
      <div className="flex gap-2">
        {!superadmin && (
          <input
            type="password"
            className="input"
            placeholder="Пароль соревнования"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onFocus={onRequireAuth}
          />
        )}
        <button
          className="btn-primary whitespace-nowrap"
          disabled={join.isPending}
          onClick={() => {
            if (onRequireAuth()) return;
            join.mutate();
          }}
        >
          Войти
        </button>
      </div>
      {error && <p className="mt-1 text-sm text-red-600">{error}</p>}
    </div>
  );
}

export default function RoomsHub() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const user = useAuth((s) => s.user);
  const superadmin = useAuth((s) => s.isSuperadmin());
  const loadMe = useAuth((s) => s.loadMe);
  const [authPrompt, setAuthPrompt] = useState(false);
  // Анониму действия недоступны — вместо них показываем окно авторизации.
  const requireAuth = () => {
    if (user) return false;
    setAuthPrompt(true);
    return true;
  };

  const mine = useQuery({
    queryKey: ["my-rooms"],
    queryFn: api.myRooms,
    enabled: !!user,
  });
  const [q, setQ] = useState("");
  const search = useQuery({
    queryKey: ["rooms-search", q],
    queryFn: () => api.listRooms(q || undefined),
  });

  const [newName, setNewName] = useState("");
  const [newPwd, setNewPwd] = useState("");
  const create = useMutation({
    // Быстрое создание из лобби — тип ЧМ по умолчанию. Полная панель создания
    // турниров (РПЛ/ЛЧ, длительность, сезон) — в /admin.
    mutationFn: () =>
      api.createTournament({
        name: newName,
        password: newPwd,
        tournament_type: "world_cup",
      }),
    onSuccess: (room) => {
      setNewName("");
      setNewPwd("");
      qc.invalidateQueries({ queryKey: ["my-rooms"] });
      loadMe();
      navigate(`/room/${room.id}`);
    },
    onError: (e: any) => alert(e.response?.data?.detail || "Не удалось создать соревнование"),
  });

  const myIds = new Set((mine.data || []).map((r) => r.id));
  const joinable = (search.data || []).filter((r) => !myIds.has(r.id));
  const activeRooms = (mine.data || []).filter((rm) => rm.is_active);
  const archivedRooms = (mine.data || []).filter((rm) => !rm.is_active);

  const refetchAll = () => {
    qc.invalidateQueries({ queryKey: ["my-rooms"] });
    qc.invalidateQueries({ queryKey: ["rooms-search"] });
    loadMe();
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Соревнования</h1>

      {authPrompt && <AuthModal onClose={() => setAuthPrompt(false)} />}

      {!user ? (
        <section className="card">
          <h2 className="mb-2 text-lg font-semibold">Добро пожаловать! 👋</h2>
          <p className="text-sm text-slate-600">
            Здесь соревнуются в прогнозах на матчи ЧМ-2026: угадывайте счёт,
            набирайте очки и поднимайтесь в таблице. Выберите соревнование ниже —
            для участия понадобится войти и ввести пароль соревнования.
          </p>
        </section>
      ) : (
        <section className="card">
          <h2 className="mb-3 text-lg font-semibold">Мои соревнования</h2>
          {mine.isLoading ? (
            <p className="text-slate-500">Загрузка…</p>
          ) : !activeRooms.length ? (
            <p className="text-slate-500">
              Вы пока не участвуете ни в одном активном соревновании. Найдите соревнование ниже и войдите по паролю.
            </p>
          ) : (
            <div className="grid gap-2">
              {activeRooms.map((room) => (
                <RoomRow
                  key={room.id}
                  room={room}
                  onOpen={() => navigate(`/room/${room.id}`)}
                />
              ))}
            </div>
          )}
        </section>
      )}

      {archivedRooms.length > 0 && (
        <section className="card">
          <h2 className="mb-3 text-lg font-semibold text-slate-500">Архив</h2>
          <div className="grid gap-2">
            {archivedRooms.map((room) => (
              <button
                key={room.id}
                onClick={() => navigate(`/room/${room.id}`)}
                className="flex w-full items-center justify-between rounded-lg border border-dashed p-3 text-left text-slate-500 hover:bg-slate-50"
              >
                <div>
                  <div className="font-medium">
                    {room.name} <span className="text-xs">(архив)</span>
                  </div>
                  <div className="text-xs">{room.member_count} участников · только просмотр</div>
                </div>
                <span>Таблица →</span>
              </button>
            ))}
          </div>
        </section>
      )}

      {superadmin && (
        <section className="card space-y-3">
          <h2 className="text-lg font-semibold">Создать соревнование</h2>
          <input
            className="input"
            placeholder="Название соревнования"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <input
            className="input"
            placeholder="Пароль для входа (мин. 4 символа)"
            value={newPwd}
            onChange={(e) => setNewPwd(e.target.value)}
          />
          <button
            className="btn-primary"
            disabled={newName.length < 2 || newPwd.length < 4 || create.isPending}
            onClick={() => create.mutate()}
          >
            {create.isPending ? "Создание…" : "Создать"}
          </button>
        </section>
      )}

      <section className="card space-y-3">
        <h2 className="text-lg font-semibold">Найти соревнование</h2>
        <input
          className="input"
          placeholder="Поиск по названию"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {search.isLoading ? (
          <p className="text-slate-500">Загрузка…</p>
        ) : !joinable.length ? (
          <p className="text-slate-500">Нет доступных соревнований.</p>
        ) : (
          <div className="grid gap-2">
            {joinable.map((room) => (
              <JoinCard
                key={room.id}
                room={room}
                onJoined={refetchAll}
                onRequireAuth={requireAuth}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
