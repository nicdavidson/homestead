"use client";

import { useState, useEffect, useMemo } from "react";
import { api } from "@/lib/api";
import type { Skill } from "@/lib/types";

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTag, setSelectedTag] = useState<string>("");
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  // Create form state
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newTags, setNewTags] = useState("");
  const [newContent, setNewContent] = useState("");
  const [saving, setSaving] = useState(false);

  async function loadSkills() {
    try {
      setLoading(true);
      const data = await api.skills.list();
      setSkills(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load skills");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSkills();
  }, []);

  const allTags = useMemo(() => {
    const tags = new Set<string>();
    skills.forEach((s) => s.tags?.forEach((t) => tags.add(t)));
    return Array.from(tags).sort();
  }, [skills]);

  const filteredSkills = useMemo(() => {
    return skills.filter((s) => {
      const matchesSearch =
        !searchQuery ||
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesTag =
        !selectedTag || (s.tags && s.tags.includes(selectedTag));
      return matchesSearch && matchesTag;
    });
  }, [skills, searchQuery, selectedTag]);

  async function handleSave(name: string, data: { description: string; content: string; tags: string[] }) {
    try {
      setSaving(true);
      await api.skills.save(name, data);
      await loadSkills();
      setEditingSkill(null);
      setShowCreate(false);
      resetCreateForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save skill");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(name: string) {
    if (!confirm(`Delete skill "${name}"?`)) return;
    try {
      await api.skills.delete(name);
      setExpandedSkill(null);
      await loadSkills();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete skill");
    }
  }

  function resetCreateForm() {
    setNewName("");
    setNewDescription("");
    setNewTags("");
    setNewContent("");
  }

  function handleCreate() {
    if (!newName.trim()) return;
    handleSave(newName.trim(), {
      description: newDescription,
      content: newContent,
      tags: newTags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
    });
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="p-6 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-neutral-100">Skills</h1>
            <p className="text-sm text-neutral-500 mt-1">
              Agent skill library ({skills.length} skills)
            </p>
          </div>
          <button
            onClick={() => {
              setShowCreate(!showCreate);
              setEditingSkill(null);
            }}
            className="px-4 py-2 rounded-lg bg-amber-500 text-neutral-950 font-medium text-sm hover:bg-amber-400 transition-colors"
          >
            New Skill
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 text-xs">
              Dismiss
            </button>
          </div>
        )}

        {/* Create Form */}
        {showCreate && (
          <div className="mb-6 p-5 rounded-xl border border-neutral-800 bg-neutral-900">
            <h2 className="text-sm font-semibold text-neutral-200 mb-4">
              Create New Skill
            </h2>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-neutral-500 mb-1">Name</label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="skill-name"
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-500/50"
                  />
                </div>
                <div>
                  <label className="block text-xs text-neutral-500 mb-1">Tags (comma separated)</label>
                  <input
                    type="text"
                    value={newTags}
                    onChange={(e) => setNewTags(e.target.value)}
                    placeholder="python, automation"
                    className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-500/50"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs text-neutral-500 mb-1">Description</label>
                <input
                  type="text"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="What this skill does"
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-500/50"
                />
              </div>
              <div>
                <label className="block text-xs text-neutral-500 mb-1">Content</label>
                <textarea
                  value={newContent}
                  onChange={(e) => setNewContent(e.target.value)}
                  placeholder="Skill content / instructions..."
                  rows={8}
                  className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-500/50 font-mono resize-y"
                />
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCreate}
                  disabled={saving || !newName.trim()}
                  className="px-4 py-2 rounded-lg bg-amber-500 text-neutral-950 font-medium text-sm hover:bg-amber-400 disabled:opacity-40 transition-colors"
                >
                  {saving ? "Saving..." : "Create"}
                </button>
                <button
                  onClick={() => {
                    setShowCreate(false);
                    resetCreateForm();
                  }}
                  className="px-4 py-2 rounded-lg bg-neutral-800 text-neutral-400 text-sm hover:text-neutral-200 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Search and Filter */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search skills..."
            className="flex-1 min-w-[200px] bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 placeholder:text-neutral-500 focus:outline-none focus:border-amber-500/50"
          />
          <select
            value={selectedTag}
            onChange={(e) => setSelectedTag(e.target.value)}
            className="text-sm bg-neutral-900 border border-neutral-700 rounded-lg px-3 py-2 text-neutral-300 focus:outline-none focus:border-amber-500/50"
          >
            <option value="">All Tags</option>
            {allTags.map((tag) => (
              <option key={tag} value={tag}>
                {tag}
              </option>
            ))}
          </select>
        </div>

        {/* Loading */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="flex items-center gap-3 text-neutral-400">
              <div className="w-5 h-5 border-2 border-amber-500/30 border-t-amber-500 rounded-full animate-spin" />
              Loading skills...
            </div>
          </div>
        ) : filteredSkills.length === 0 ? (
          <div className="text-center py-20">
            <p className="text-neutral-500 text-lg">No skills found</p>
            <p className="text-neutral-600 text-sm mt-1">
              {searchQuery || selectedTag
                ? "Try adjusting your search"
                : "Create your first skill"}
            </p>
          </div>
        ) : (
          /* Skills Grid */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSkills.map((skill) => (
              <div
                key={skill.name}
                className={`rounded-xl border p-4 transition-colors cursor-pointer ${
                  expandedSkill === skill.name
                    ? "border-amber-500/30 bg-amber-500/5"
                    : "border-neutral-800 bg-neutral-900 hover:border-neutral-700"
                }`}
                onClick={() =>
                  setExpandedSkill(
                    expandedSkill === skill.name ? null : skill.name
                  )
                }
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-neutral-100 text-sm">
                    {skill.name}
                  </h3>
                </div>
                <p className="text-xs text-neutral-400 mb-3 line-clamp-2">
                  {skill.description}
                </p>
                {skill.tags && skill.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-3">
                    {skill.tags.map((tag) => (
                      <span
                        key={tag}
                        className="text-[10px] px-2 py-0.5 rounded-full bg-neutral-800 text-neutral-400"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Expanded Content */}
                {expandedSkill === skill.name && (
                  <div
                    className="mt-3 pt-3 border-t border-neutral-800"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {editingSkill?.name === skill.name ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editingSkill.description}
                          onChange={(e) =>
                            setEditingSkill({
                              ...editingSkill,
                              description: e.target.value,
                            })
                          }
                          className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/50"
                        />
                        <input
                          type="text"
                          value={editingSkill.tags.join(", ")}
                          onChange={(e) =>
                            setEditingSkill({
                              ...editingSkill,
                              tags: e.target.value
                                .split(",")
                                .map((t) => t.trim())
                                .filter(Boolean),
                            })
                          }
                          placeholder="Tags (comma separated)"
                          className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-sm text-neutral-100 focus:outline-none focus:border-amber-500/50"
                        />
                        <textarea
                          value={editingSkill.content}
                          onChange={(e) =>
                            setEditingSkill({
                              ...editingSkill,
                              content: e.target.value,
                            })
                          }
                          rows={10}
                          className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-xs text-neutral-100 font-mono focus:outline-none focus:border-amber-500/50 resize-y"
                        />
                        <div className="flex gap-2">
                          <button
                            onClick={() =>
                              handleSave(editingSkill.name, {
                                description: editingSkill.description,
                                content: editingSkill.content,
                                tags: editingSkill.tags,
                              })
                            }
                            disabled={saving}
                            className="px-3 py-1.5 rounded-lg bg-amber-500 text-neutral-950 text-xs font-medium hover:bg-amber-400 disabled:opacity-40 transition-colors"
                          >
                            {saving ? "Saving..." : "Save"}
                          </button>
                          <button
                            onClick={() => setEditingSkill(null)}
                            className="px-3 py-1.5 rounded-lg bg-neutral-800 text-neutral-400 text-xs hover:text-neutral-200 transition-colors"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <pre className="p-3 rounded-lg bg-neutral-800 text-xs text-neutral-300 overflow-x-auto whitespace-pre-wrap max-h-64 overflow-y-auto font-mono">
                          {skill.content}
                        </pre>
                        <div className="flex gap-2 mt-3">
                          <button
                            onClick={() => setEditingSkill({ ...skill })}
                            className="px-3 py-1.5 rounded-lg bg-neutral-800 text-neutral-300 text-xs hover:bg-neutral-700 transition-colors"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDelete(skill.name)}
                            className="px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 text-xs hover:bg-red-500/20 transition-colors"
                          >
                            Delete
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
