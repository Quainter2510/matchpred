import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../api/endpoints";
import { useAuth } from "../../store/auth";

export default function AdminMembers() {
  const qc = useQueryClient();
  const isSuper = useAuth((s) => s.isSuperadmin());
  const members = useQuery({ queryKey: ["members"], queryFn: api.members });

  const role = useMutation({
    mutationFn: ({ uid, r }: { uid: string; r: string }) => api.changeRole(uid, r),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members"] }),
  });
  const remove = useMutation({
    mutationFn: (uid: string) => api.removeMember(uid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members"] }),
  });
  const participation = useMutation({
    mutationFn: ({ uid, confirmed }: { uid: string; confirmed: boolean }) =>
      api.setParticipation(uid, confirmed),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["members"] });
      qc.invalidateQueries({ queryKey: ["leaderboard"] });
    },
  });
  const transfer = useMutation({
    mutationFn: (uid: string) => api.transferSuperadmin(uid),
    onSuccess: () => {
      alert("Роль суперадмина передана");
      qc.invalidateQueries({ queryKey: ["members"] });
    },
  });

  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-slate-500">
            <th className="py-2">Игрок</th>
            <th>Роль</th>
            <th className="text-center">Участие</th>
            <th>Очки</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(members.data || []).map((m) => (
            <tr key={m.user_id} className="border-b">
              <td className="py-2">{m.nickname}</td>
              <td>
                {m.system_role === "superadmin" ? (
                  <span className="font-semibold text-brand">Суперадмин</span>
                ) : (
                  <select
                    className="rounded border px-2 py-1"
                    value={m.tournament_role}
                    onChange={(e) =>
                      role.mutate({ uid: m.user_id, r: e.target.value })
                    }
                  >
                    <option value="player">Игрок</option>
                    <option value="admin">Админ</option>
                  </select>
                )}
              </td>
              <td className="text-center">
                <label className="inline-flex cursor-pointer items-center gap-1">
                  <input
                    type="checkbox"
                    className="h-4 w-4 accent-emerald-600"
                    checked={m.participation_confirmed}
                    disabled={participation.isPending}
                    onChange={(e) =>
                      participation.mutate({
                        uid: m.user_id,
                        confirmed: e.target.checked,
                      })
                    }
                  />
                </label>
              </td>
              <td>{m.total_points}</td>
              <td className="space-x-2 text-right">
                {isSuper && m.system_role !== "superadmin" && (
                  <button
                    className="text-xs text-brand hover:underline"
                    onClick={() => {
                      if (confirm(`Передать роль суперадмина игроку ${m.nickname}?`))
                        transfer.mutate(m.user_id);
                    }}
                  >
                    Сделать суперадмином
                  </button>
                )}
                {m.system_role !== "superadmin" && (
                  <button
                    className="text-xs text-red-600 hover:underline"
                    onClick={() => {
                      if (confirm(`Удалить ${m.nickname} из турнира?`))
                        remove.mutate(m.user_id);
                    }}
                  >
                    Удалить
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
