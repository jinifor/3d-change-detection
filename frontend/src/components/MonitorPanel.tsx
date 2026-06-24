import { useMutation } from "@tanstack/react-query";
import { Ban, Check, Radio } from "lucide-react";
import { sendRegistrationDecision } from "../api/client";
import { useAppStore } from "../store/appStore";

const stages = [
  "UPLOADED",
  "VALIDATING",
  "REGISTERING",
  "CONVERTING_COPC",
  "GENERATING_TILES",
  "DETECTING_CHANGE",
  "CLUSTERING",
  "PUBLISHING",
  "COMPLETED",
];

export function MonitorPanel() {
  const config = useAppStore((state) => state.config);
  const job = useAppStore((state) => state.job);
  const events = useAppStore((state) => state.events);
  const registrationGate = useAppStore((state) => state.registrationGate);
  const setRegistrationGate = useAppStore((state) => state.setRegistrationGate);
  const setJob = useAppStore((state) => state.setJob);

  const decisionMutation = useMutation({
    mutationFn: (decision: "continue" | "abort") =>
      sendRegistrationDecision(config, registrationGate!.jobId, decision),
    onSuccess: (updatedJob) => {
      setJob(updatedJob);
      setRegistrationGate(null);
    },
  });

  const currentIndex = stages.findIndex((stage) => stage === job?.status);

  return (
    <div className="monitor">
      <div className="job-summary">
        <div>
          <span>Job</span>
          <strong>{job?.id.slice(0, 8) ?? "not started"}</strong>
        </div>
        <div>
          <span>Progress</span>
          <strong>{job?.progress ?? 0}%</strong>
        </div>
      </div>

      {registrationGate && (
        <div className="decision-box">
          <div>
            <strong>Registration gate</strong>
            <span>
              RMSE {registrationGate.rmse.toFixed(3)}m /{" "}
              {registrationGate.threshold.toFixed(3)}m
            </span>
          </div>
          <div className="button-row">
            <button
              className="secondary-button"
              type="button"
              onClick={() => decisionMutation.mutate("abort")}
            >
              <Ban size={15} />
              Abort
            </button>
            <button
              className="primary-button"
              type="button"
              onClick={() => decisionMutation.mutate("continue")}
            >
              <Check size={15} />
              Continue
            </button>
          </div>
        </div>
      )}

      <ol className="stage-list">
        {stages.map((stage, index) => {
          const done = currentIndex > index || job?.status === "COMPLETED";
          const active = currentIndex === index;
          return (
            <li className={done ? "done" : active ? "active" : ""} key={stage}>
              <Radio size={13} />
              <span>{stage}</span>
            </li>
          );
        })}
      </ol>

      <div className="event-list">
        {events.length === 0 && <p className="muted">No events yet</p>}
        {events.map((event) => (
          <div className="event-row" key={event.id}>
            <time>{new Date(event.at).toLocaleTimeString()}</time>
            <span>{event.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
