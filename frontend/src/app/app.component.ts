import { Component, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, Todo, TodoStats } from './api.service';
import {
  computeAdvancedStats as computeAdvancedStatsFn,
  AdvancedStats,
} from './stats-utils';

type HealthStatus = { status: string; env: string };

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css',
})
export class AppComponent {
  title = 'TP05 – Angular + FastAPI (v2)';

  // Estado principal
  health = signal<HealthStatus | null>(null);
  stats = signal<TodoStats | null>(null);
  todos = signal<Todo[]>([]);
  advancedStats = signal<AdvancedStats | null>(null);

  loading = signal<boolean>(false);
  error: string | null = null;

  // Formulario de alta
  newTitle = '';
  newDescription = ''; // soporte de descripción

  // Filtros
  filterText = '';
  filterDone: 'all' | 'done' | 'pending' = 'all';

  constructor(private api: ApiService) {
    // Carga inicial
    this.refresh();
  }

  private recomputeAdvancedStats(): void {
    const current = this.todos();
    if (!current || current.length === 0) {
      this.advancedStats.set(null);
      return;
    }
    this.advancedStats.set(computeAdvancedStatsFn(current));
  }

  refresh(): void {
    // Limpia errores previos
    this.error = null;
    this.loading.set(true);

    // Health
    this.api.health().subscribe({
      next: (h: HealthStatus) => this.health.set(h),
      error: () => {
        this.error = 'No se pudo obtener el estado de la API';
      },
    });

    // Todos
    this.api.listTodos().subscribe({
      next: (list) => {
        this.todos.set(list);
        this.recomputeAdvancedStats();
      },
      error: () => {
        this.error = 'No se pudo obtener los todos';
      },
      complete: () => {
        this.loading.set(false);
      },
    });

    // Resumen básico
    this.api.stats().subscribe({
      next: (s) => this.stats.set(s),
      error: () => {
        if (!this.error) {
          this.error = 'No se pudieron obtener las estadísticas';
        }
      },
    });
  }

  add(): void {
    const trimmedTitle = (this.newTitle || '').trim();
    const trimmedDescription = (this.newDescription || '').trim();

    if (!trimmedTitle) {
      // No llamamos al servicio si el título está vacío o en blanco
      return;
    }

    this.loading.set(true);
    this.error = null;

    this.api
      .addTodo(trimmedTitle, trimmedDescription || undefined)
      .subscribe({
        next: (todo) => {
          this.todos.update((current) => [...current, todo]);

          // Limpiamos el formulario
          this.newTitle = '';
          this.newDescription = '';

          // Refrescamos stats básicas
          this.api.stats().subscribe({
            next: (s) => this.stats.set(s),
            error: () => {
              if (!this.error) {
                this.error = 'No se pudieron obtener las estadísticas';
              }
            },
          });

          this.recomputeAdvancedStats();
        },
        error: (err) => {
          const maybeStatus = (err as any)?.status;
          const maybeDetail = (err as any)?.error?.detail;

          if (maybeStatus === 400 && maybeDetail === 'title must be unique') {
            this.error = 'Ya existe una tarea con ese título';
          } else {
            this.error = 'No se pudo crear el todo';
          }

          this.loading.set(false);
        },
        complete: () => {
          this.loading.set(false);
        },
      });
  }

  toggle(todo: Todo): void {
    this.loading.set(true);
    this.error = null;

    this.api.toggleTodo(todo.id).subscribe({
      next: (updated) => {
        this.todos.update((current) =>
          current.map((t) => (t.id === updated.id ? updated : t)),
        );

        // Refrescamos stats
        this.api.stats().subscribe({
          next: (s) => this.stats.set(s),
          error: () => {
            if (!this.error) {
              this.error = 'No se pudieron obtener las estadísticas';
            }
          },
        });

        this.recomputeAdvancedStats();
      },
      error: () => {
        this.error = 'No se pudo cambiar el estado del todo';
        this.loading.set(false);
      },
      complete: () => {
        this.loading.set(false);
      },
    });
  }

  applyFilters(): void {
    const qRaw = this.filterText ?? '';
    const q = qRaw.trim();

    let doneFilter: boolean | undefined;

    if (this.filterDone === 'done') {
      doneFilter = true;
    } else if (this.filterDone === 'pending') {
      doneFilter = false;
    }

    const filters: { q?: string; done?: boolean } = {};

    if (q) {
      filters.q = q;
    }

    if (doneFilter !== undefined) {
      filters.done = doneFilter;
    }

    this.loading.set(true);
    this.error = null;

    this.api.searchTodos(filters).subscribe({
      next: (list) => {
        this.todos.set(list);
        this.recomputeAdvancedStats();
      },
      error: () => {
        this.error = 'No se pudo filtrar los todos';
      },
      complete: () => {
        this.loading.set(false);
      },
    });
  }
}
