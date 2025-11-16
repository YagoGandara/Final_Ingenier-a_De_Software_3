import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../environments/environment';

export type Todo = {
  id: number;
  title: string;
  done: boolean;
  description?: string;
};

export interface TodoStats {
  total: number;
  done: number;
  pending: number;
}

export interface TodoSearchFilters {
  q?: string;
  done?: boolean;
}

declare global {
  interface Window {
    __env?: { apiBase?: string };
  }
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private base = (window.__env?.apiBase || environment.apiBaseUrl || '').replace(
    /\/+$/,
    '',
  );

  constructor(private http: HttpClient) {}

  health() {
    return this.http.get(`${this.base}/healthz`);
  }

  listTodos() {
    return this.http.get<Todo[]>(`${this.base}/api/todos`);
  }

  addTodo(title: string) {
    return this.http.post<Todo>(`${this.base}/api/todos`, { title });
  }

  stats() {
    return this.http.get<TodoStats>(`${this.base}/api/todos/stats`);
  }

  searchTodos(filters: TodoSearchFilters = {}) {
    const params: any = {};

    const trimmed = filters.q?.trim();
    if (trimmed) {
      params.q = trimmed;
    }

    if (filters.done !== undefined && filters.done !== null) {
      params.done = filters.done;
    }

    return this.http.get<Todo[]>(`${this.base}/api/todos/search`, { params });
  }

  toggleTodo(id: number) {
    return this.http.patch<Todo>(`${this.base}/api/todos/${id}/toggle`, {});
  }
}
