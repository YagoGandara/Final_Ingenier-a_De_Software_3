import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';
import { HttpClient } from '@angular/common/http';
import { ApiService, Todo } from './api.service';
import { environment } from '../environments/environment';

describe('ApiService', () => {
  let service: ApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    (window as any).__env = { apiBase: 'http://fake-api///' };

    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [ApiService],
    });

    service = TestBed.inject(ApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    (window as any).__env = undefined;
  });

  it('health() debe hacer GET /healthz usando la base normalizada sin barras duplicadas', () => {
    service.health().subscribe();

    const req = http.expectOne('http://fake-api/healthz');
    expect(req.request.method).toBe('GET');

    req.flush({ status: 'ok' });
  });

  it('listTodos() debe hacer GET /api/todos y devolver la lista tipada', () => {
    const mock: Todo[] = [
      { id: 1, title: 'A', done: false },
      { id: 2, title: 'B', done: true },
    ];

    let result: Todo[] | undefined;

    service.listTodos().subscribe((todos) => (result = todos));

    const req = http.expectOne('http://fake-api/api/todos');
    expect(req.request.method).toBe('GET');

    req.flush(mock);

    expect(result).toEqual(mock);
  });

  it('addTodo() incluye description cuando se provee y la trimea', () => {
    const title = 'Tarea con descripción';
    const description = '  Detalle importante  ';

    service.addTodo(title, description).subscribe();

    const req = http.expectOne('http://fake-api/api/todos');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({
      title,
      description: 'Detalle importante',
    });

    req.flush({
      id: 2,
      title,
      done: false,
      description: 'Detalle importante',
    } as Todo);
  });

  it('stats() debe hacer GET /api/todos/stats', () => {
    service.stats().subscribe();

    const req = http.expectOne('http://fake-api/api/todos/stats');
    expect(req.request.method).toBe('GET');

    req.flush({ total: 3, done: 1, pending: 2 });
  });

  it('searchTodos() sin filtros debe llamar /api/todos/search sin params', () => {
    service.searchTodos().subscribe();

    const req = http.expectOne((r) => r.url === 'http://fake-api/api/todos/search');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.keys().length).toBe(0);

    req.flush([]);
  });

  it('searchTodos() con q debe enviar el parámetro q trimmeado', () => {
    service.searchTodos({ q: '  pan  ' }).subscribe();

    const req = http.expectOne((r) => r.url === 'http://fake-api/api/todos/search');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('q')).toBe('pan');

    req.flush([]);
  });

  it('searchTodos() con done=true debe enviar el parámetro done=true', () => {
    service.searchTodos({ done: true }).subscribe();

    const req = http.expectOne((r) => r.url === 'http://fake-api/api/todos/search');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('done')).toBe('true');

    req.flush([]);
  });

  it('searchTodos() con q y done=false debe enviar ambos parámetros', () => {
    service.searchTodos({ q: 'pan', done: false }).subscribe();

    const req = http.expectOne((r) => r.url === 'http://fake-api/api/todos/search');
    expect(req.request.method).toBe('GET');
    expect(req.request.params.get('q')).toBe('pan');
    expect(req.request.params.get('done')).toBe('false');

    req.flush([]);
  });

  it('searchTodos() ignora q cuando viene sólo espacios en blanco', () => {
    service.searchTodos({ q: '   ' }).subscribe();

    const req = http.expectOne((r) => r.url === 'http://fake-api/api/todos/search');
    expect(req.request.params.keys().length).toBe(0);

    req.flush([]);
  });

  it('toggleTodo() debe hacer PATCH /api/todos/{id}/toggle con body vacío', () => {
    service.toggleTodo(42).subscribe();

    const req = http.expectOne('http://fake-api/api/todos/42/toggle');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({});

    req.flush({ id: 42, title: 'algo', done: true });
  });

  it('cuando no hay window.__env debe usar environment.apiBaseUrl como base', () => {
    (window as any).__env = undefined;

    const httpClient = TestBed.inject(HttpClient);
    const svc = new ApiService(httpClient);

    svc.health().subscribe();

    const expectedBase = (environment.apiBaseUrl || '').replace(/\/+$/, '');
    const req = http.expectOne(`${expectedBase}/healthz`);
    expect(req.request.method).toBe('GET');

    req.flush({ status: 'ok' });
  });
});
