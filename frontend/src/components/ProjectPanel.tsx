import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Pencil, RefreshCw, Trash2, X } from "lucide-react";
import { deleteProject, listProjects, updateProject } from "../api/client";
import { useAppStore } from "../store/appStore";
import type { ProjectRead } from "../types";

const statusOptions = [
  { label: "All", value: "" },
  { label: "Completed", value: "COMPLETED" },
  { label: "Failed", value: "FAILED" },
];

export function ProjectPanel() {
  const queryClient = useQueryClient();
  const config = useAppStore((state) => state.config);
  const currentProject = useAppStore((state) => state.project);
  const setProject = useAppStore((state) => state.setProject);
  const setJob = useAppStore((state) => state.setJob);
  const setAssets = useAppStore((state) => state.setAssets);
  const setCandidates = useAppStore((state) => state.setCandidates);
  const setRegistrationGate = useAppStore((state) => state.setRegistrationGate);
  const setSelectedCandidateId = useAppStore((state) => state.setSelectedCandidateId);
  const clearEvents = useAppStore((state) => state.clearEvents);

  const [statusFilter, setStatusFilter] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingName, setEditingName] = useState("");

  const projectsQuery = useQuery({
    queryKey: ["projects", statusFilter],
    queryFn: () => listProjects(config, statusFilter || undefined),
  });

  const updateMutation = useMutation({
    mutationFn: ({ projectId, name }: { projectId: string; name: string }) =>
      updateProject(config, projectId, name),
    onSuccess: (project) => {
      if (currentProject?.id === project.id) setProject(project);
      setEditingId(null);
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (projectId: string) => deleteProject(config, projectId),
    onSuccess: (_, projectId) => {
      if (currentProject?.id === projectId) {
        setProject(null);
        setJob(null);
        setAssets(null);
        setCandidates([]);
        setSelectedCandidateId(null);
        setRegistrationGate(null);
        clearEvents();
      }
      void queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  function selectProject(project: ProjectRead) {
    setProject(project);
    setJob(null);
    setAssets(null);
    setCandidates([]);
    setSelectedCandidateId(null);
    setRegistrationGate(null);
    clearEvents();
  }

  function beginEdit(project: ProjectRead) {
    setEditingId(project.id);
    setEditingName(project.name);
  }

  function submitEdit(event: FormEvent<HTMLFormElement>, projectId: string) {
    event.preventDefault();
    const name = editingName.trim();
    if (!name || updateMutation.isPending) return;
    updateMutation.mutate({ projectId, name });
  }

  function removeProject(project: ProjectRead) {
    if (deleteMutation.isPending) return;
    const confirmed = window.confirm(`Delete project "${project.name}"?`);
    if (confirmed) deleteMutation.mutate(project.id);
  }

  const projects = projectsQuery.data ?? [];
  const mutationError = updateMutation.error ?? deleteMutation.error;

  return (
    <div className="project-panel">
      <div className="project-filter-row">
        <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
          {statusOptions.map((option) => (
            <option key={option.value || "all"} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <button
          className="icon-button"
          type="button"
          title="Refresh projects"
          onClick={() => void projectsQuery.refetch()}
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {projectsQuery.error && <p className="error-text">{projectsQuery.error.message}</p>}
      {mutationError && <p className="error-text">{mutationError.message}</p>}
      {projectsQuery.isLoading && <p className="muted">Loading projects</p>}
      {!projectsQuery.isLoading && projects.length === 0 && <p className="muted">No projects</p>}

      <div className="project-list">
        {projects.map((project) => {
          const selected = currentProject?.id === project.id;
          const editing = editingId === project.id;
          const canDelete = ["UPLOADED", "COMPLETED", "FAILED"].includes(project.status);
          return (
            <div className={selected ? "project-row selected" : "project-row"} key={project.id}>
              {editing ? (
                <form className="project-edit-form" onSubmit={(event) => submitEdit(event, project.id)}>
                  <input
                    autoFocus
                    value={editingName}
                    onChange={(event) => setEditingName(event.target.value)}
                  />
                  <button className="icon-button" type="submit" title="Save project name">
                    <Check size={15} />
                  </button>
                  <button
                    className="icon-button"
                    type="button"
                    title="Cancel editing"
                    onClick={() => setEditingId(null)}
                  >
                    <X size={15} />
                  </button>
                </form>
              ) : (
                <>
                  <button
                    className="project-select"
                    type="button"
                    onClick={() => selectProject(project)}
                  >
                    <strong>{project.name}</strong>
                    <span>
                      {project.status} · {new Date(project.updated_at).toLocaleString()}
                    </span>
                  </button>
                  <div className="project-actions">
                    <button
                      className="icon-button"
                      type="button"
                      title="Rename project"
                      onClick={() => beginEdit(project)}
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      className="icon-button danger"
                      type="button"
                      title={canDelete ? "Delete project" : "Cannot delete while job is active"}
                      disabled={!canDelete || deleteMutation.isPending}
                      onClick={() => removeProject(project)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
