import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, PlugZap, Settings2, XCircle } from "lucide-react";
import { checkHealth } from "../api/client";
import { useAppStore } from "../store/appStore";

export function TopBar() {
  const config = useAppStore((state) => state.config);
  const setConfig = useAppStore((state) => state.setConfig);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [form, setForm] = useState(config);

  const healthQuery = useQuery({
    queryKey: ["health", config.baseUrl],
    queryFn: () => checkHealth(config),
    refetchInterval: 15_000,
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setConfig(form);
    setSettingsOpen(false);
  }

  const online = healthQuery.data?.status === "ok";

  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">3D</div>
        <div>
          <strong>Change Detection</strong>
          <span>LiDAR Review Console</span>
        </div>
      </div>

      <div className="topbar-actions">
        <div className={online ? "health online" : "health offline"}>
          {online ? <CheckCircle2 size={15} /> : <XCircle size={15} />}
          <span>{online ? "API online" : "API offline"}</span>
        </div>
        <button
          className="icon-button"
          type="button"
          title="API settings"
          onClick={() => setSettingsOpen((value) => !value)}
        >
          <Settings2 size={17} />
        </button>
      </div>

      {settingsOpen && (
        <form className="settings-popover" onSubmit={submit}>
          <label>
            <span>API Base</span>
            <input
              value={form.baseUrl}
              placeholder="empty uses Vite proxy"
              onChange={(event) => setForm({ ...form, baseUrl: event.target.value })}
            />
          </label>
          <label>
            <span>API Key</span>
            <input
              value={form.apiKey}
              onChange={(event) => setForm({ ...form, apiKey: event.target.value })}
            />
          </label>
          <label>
            <span>SSE Token</span>
            <input
              value={form.sseToken}
              onChange={(event) => setForm({ ...form, sseToken: event.target.value })}
            />
          </label>
          <button className="primary-button" type="submit">
            <PlugZap size={16} />
            Apply
          </button>
        </form>
      )}
    </header>
  );
}
