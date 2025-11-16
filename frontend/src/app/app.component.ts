import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Todo, TodoStats } from './api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  title = 'TP05 – Angular + FastAPI';

  health = signal<any | null>(null);
  todos = signal<Todo[]>([]);
  loading = signal(false);

  stats = signal<TodoStats | null>(null);
  filterText = '';
  filterDone: 'all' | 'done' | 'pending' = 'all';
  error: string | null = null;

  newTitle = '';

  constructor(private api: ApiService) {
    this.refresh();
  }

  refresh() {
    this.error = null;

    this.api.health().subscribe({
      next: (h) => this.health.set(h),
      error: () => {
        this.error = 'No se pudo obtener el estado de la API';
      },
    });

    this.api.listTodos().subscribe({
      next: (list) => this.todos.set(list),
      error: () => {
        this.error = 'No se pudo obtener los todos';
      },
    });

    this.api.stats().subscribe({
      next: (s) => this.stats.set(s),
      error: () => {
        this.error = 'No se pudo obtener las estadísticas';
      },
    });
  }

  add() {
    const trimmed = this.newTitle.trim();
    if (!trimmed) return;

    this.error = null;
    this.loading.set(true);

    this.api.addTodo(trimmed).subscribe({
      next: (t) => {
        this.todos.update((v) => [...v, t]);
        this.newTitle = '';

        this.api.stats().subscribe({
          next: (s) => this.stats.set(s),
          error: () => {
            if (!this.error) {
              this.error = 'No se pudieron actualizar las estadísticas';
            }
          },
        });

        this.loading.set(false);
      },
      error: (err: any) => {
        if (
          err?.status === 400 &&
          err?.error?.detail === 'title must be unique'
        ) {
          this.error = 'Ya existe una tarea con ese título';
        } else {
          this.error = 'No se pudo crear el todo';
        }
        this.loading.set(false);
      },
    });
  }

  toggle(todo: Todo) {
    this.error = null;
    this.loading.set(true);

    this.api.toggleTodo(todo.id).subscribe({
      next: (updated) => {
        this.todos.update((list) =>
          list.map((t) => (t.id === updated.id ? updated : t)),
        );

        this.api.stats().subscribe({
          next: (s) => this.stats.set(s),
          error: () => {
            if (!this.error) {
              this.error = 'No se pudieron actualizar las estadísticas';
            }
          },
        });

        this.loading.set(false);
      },
      error: () => {
        this.error = 'No se pudo cambiar el estado del todo';
        this.loading.set(false);
      },
    });
  }

  applyFilters() {
    this.error = null;

    const q = this.filterText.trim() || undefined;
    let doneFilter: boolean | undefined;

    if (this.filterDone === 'done') {
      doneFilter = true;
    } else if (this.filterDone === 'pending') {
      doneFilter = false;
    }

    this.loading.set(true);
    this.api.searchTodos({ q, done: doneFilter }).subscribe({
      next: (list) => this.todos.set(list),
      error: () => {
        this.error = 'No se pudo filtrar los todos';
      },
      complete: () => this.loading.set(false),
    });
  }
}
