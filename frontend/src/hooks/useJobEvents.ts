import { useEffect } from "react";
import type { ApiConfig, JobEvent, JobRead, ProjectRead } from "../types";
import { getJob, getProject } from "../api/client";
import { useAppStore } from "../store/appStore";

function eventSourceUrl(config: ApiConfig, jobId: string): string {
  const baseUrl = config.baseUrl.replace(/\/$/, "");
  const token = encodeURIComponent(config.sseToken || config.apiKey);
  return `${baseUrl}/api/jobs/${jobId}/events?token=${token}`;
}

export function useJobEvents(jobId: string | null, projectId: string | null): void {
  const config = useAppStore((state) => state.config);
  const addEvent = useAppStore((state) => state.addEvent);
  const setJob = useAppStore((state) => state.setJob);
  const setProject = useAppStore((state) => state.setProject);
  const setRegistrationGate = useAppStore((state) => state.setRegistrationGate);

  useEffect(() => {
    if (!jobId) return;

    const source = new EventSource(eventSourceUrl(config, jobId));

    source.onmessage = async (message) => {
      let event: JobEvent;
      try {
        event = JSON.parse(message.data) as JobEvent;
      } catch {
        return;
      }

      addEvent(event);
      const typed = event as Record<string, unknown>;

      if (typed.type === "registration_quality" && typed.passed === false) {
        setRegistrationGate({
          jobId: String(typed.job_id),
          rmse: Number(typed.rmse),
          threshold: Number(typed.threshold),
        });
      }

      if (typed.type === "registration_decision") {
        setRegistrationGate(null);
      }

      if (typed.type === "job_progress") {
        setJob((await getJob(config, String(typed.job_id))) as JobRead);
        if (projectId) {
          setProject((await getProject(config, projectId)) as ProjectRead);
        }
      }

      if (typed.type === "job_complete" || typed.type === "job_failed") {
        setJob((await getJob(config, String(typed.job_id))) as JobRead);
        if (projectId) {
          setProject((await getProject(config, projectId)) as ProjectRead);
        }
      }
    };

    source.onerror = () => {
      source.close();
    };

    return () => source.close();
  }, [addEvent, config, jobId, projectId, setJob, setProject, setRegistrationGate]);
}
