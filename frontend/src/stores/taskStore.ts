import { create } from 'zustand';
import type { Task, TaskListParams } from '@/types/task';

interface TaskState {
  tasks: Task[];
  currentTask: Task | null;
  filters: TaskListParams;
  setFilters: (filters: TaskListParams) => void;
  setTasks: (tasks: Task[]) => void;
  setCurrentTask: (task: Task | null) => void;
  addTask: (task: Task) => void;
  updateTask: (task: Task) => void;
  removeTask: (id: number) => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  tasks: [],
  currentTask: null,
  filters: { status: 'all', page: 1, pageSize: 10 },
  setFilters: (filters) => set({ filters }),
  setTasks: (tasks) => set({ tasks }),
  setCurrentTask: (task) => set({ currentTask: task }),
  addTask: (task) => set((s) => ({ tasks: [task, ...s.tasks] })),
  updateTask: (task) =>
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === task.id ? task : t)),
      currentTask: s.currentTask?.id === task.id ? task : s.currentTask,
    })),
  removeTask: (id) =>
    set((s) => ({ tasks: s.tasks.filter((t) => t.id !== id) })),
}));
