import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { AppComponent } from './app.component';
import { ApiService, Todo, TodoStats } from './api.service';

class ApiServiceStub {
  health = jasmine.createSpy('health').and.returnValue(
    of({ status: 'ok', env: 'test' }),
  );

  listTodos = jasmine.createSpy('listTodos').and.returnValue(
    of<Todo[]>([{ id: 1, title: 'Tarea inicial', done: false }]),
  );

  addTodo = jasmine
    .createSpy('addTodo')
    .and.callFake((title: string) =>
      of<Todo>({ id: 2, title, done: false }),
    );

  stats = jasmine.createSpy('stats').and.returnValue(
    of<TodoStats>({ total: 1, done: 0, pending: 1 }),
  );

  searchTodos = jasmine.createSpy('searchTodos').and.returnValue(
    of<Todo[]>([{ id: 10, title: 'Filtrado', done: true }]),
  );

  toggleTodo = jasmine
    .createSpy('toggleTodo')
    .and.returnValue(of<Todo>({ id: 1, title: 'Tarea inicial', done: true }));
}

describe('AppComponent', () => {
  let fixture: ComponentFixture<AppComponent>;
  let component: AppComponent;
  let api: ApiServiceStub;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [{ provide: ApiService, useClass: ApiServiceStub }],
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
    api = TestBed.inject(ApiService) as unknown as ApiServiceStub;
  });

  it('debe crearse', () => {
    expect(component).toBeTruthy();
  });

  it('el constructor debe llamar health(), listTodos() y stats() una vez', () => {
    expect(api.health.calls.count()).toBe(1);
    expect(api.listTodos.calls.count()).toBe(1);
    expect(api.stats.calls.count()).toBe(1);
  });

  it('refresh() debe poblar health con el valor devuelto por el servicio', () => {
    component.refresh();
    expect(component.health()).toEqual({ status: 'ok', env: 'test' });
  });

  it('refresh() debe poblar todos() con la lista inicial', () => {
    component.refresh();
    expect(component.todos().length).toBe(1);
    expect(component.todos()[0].title).toBe('Tarea inicial');
  });

  it('refresh() debe poblar stats() con los valores devueltos por el servicio', () => {
    component.refresh();
    const stats = component.stats();
    expect(stats).toEqual({ total: 1, done: 0, pending: 1 });
  });

  it('add() no debe llamar al ApiService si el título está vacío o en blanco', () => {
    component.newTitle = '   ';
    component.add();
    expect(api.addTodo).not.toHaveBeenCalled();
  });

  it('add() debe trim()ear el título y llamar al ApiService con el título normalizado', () => {
    component.newTitle = '  Nueva tarea  ';
    component.newDescription = '   '; // sin descripción efectiva

    component.add();

    expect(api.addTodo).toHaveBeenCalledWith('Nueva tarea', undefined);
  });


  it('add() debe agregar el todo devuelto a la lista existente', () => {
    component.newTitle = 'Nueva tarea';

    component.add();

    const todos = component.todos();
    expect(todos.length).toBe(2);
    expect(todos[1].title).toBe('Nueva tarea');
  });

  it('add() debe limpiar newTitle luego de agregar un todo', () => {
    component.newTitle = 'Nueva tarea';
    component.add();
    expect(component.newTitle).toBe('');
  });

  it('add() debe dejar loading() en false al completar la operación exitosa', () => {
    component.newTitle = 'Nueva tarea';
    component.add();
    expect(component.loading()).toBeFalse();
  });

  it('add() debe llamar nuevamente a stats() para refrescar el resumen después de agregar un todo', () => {
    const before = api.stats.calls.count();

    component.newTitle = 'Nueva tarea';
    component.add();

    const after = api.stats.calls.count();
    expect(after).toBe(before + 1);
  });

  it('add() debe setear un mensaje de error genérico cuando el servicio falla', () => {
    (api.addTodo as jasmine.Spy).and.returnValue(
      throwError(() => new Error('boom')),
    );

    component.newTitle = 'Nueva tarea';
    component.add();

    expect(component.error).toBe('No se pudo crear el todo');
    expect(component.loading()).toBeFalse();
  });

  it('add() debe setear un mensaje específico cuando el backend responde título duplicado', () => {
    const duplicatedError = {
      status: 400,
      error: { detail: 'title must be unique' },
    };

    (api.addTodo as jasmine.Spy).and.returnValue(
      throwError(() => duplicatedError),
    );

    component.newTitle = 'Repetida';
    component.add();

    expect(component.error).toBe('Ya existe una tarea con ese título');
    expect(component.loading()).toBeFalse();
  });

    it('add() debe enviar también la descripción cuando se completa y limpiar ambos campos', () => {
    component.newTitle = 'Nueva con desc';
    component.newDescription = '  Detalle importante  ';

    component.add();

    expect(api.addTodo).toHaveBeenCalledWith(
      'Nueva con desc',
      'Detalle importante',
    );
    expect(component.newTitle).toBe('');
    expect(component.newDescription).toBe('');
  });


  it('toggle() debe llamar al ApiService con el id correcto', () => {
    const todo = { id: 1, title: 'Tarea inicial', done: false };

    component.toggle(todo);

    expect(api.toggleTodo).toHaveBeenCalledWith(1);
  });

  it('toggle() debe actualizar el todo en la lista con el valor devuelto por el servicio', () => {
    const before = component.todos()[0];
    expect(before.done).toBeFalse();

    component.toggle(before);

    const after = component.todos()[0];
    expect(after.done).toBeTrue();
  });

  it('toggle() debe llamar nuevamente a stats() para refrescar el resumen', () => {
    const before = api.stats.calls.count();

    const todo = component.todos()[0];
    component.toggle(todo);

    const after = api.stats.calls.count();
    expect(after).toBe(before + 1);
  });

  it('toggle() debe setear un mensaje de error y dejar loading=false cuando el servicio falla', () => {
    (api.toggleTodo as jasmine.Spy).and.returnValue(
      throwError(() => new Error('boom')),
    );

    const todo = component.todos()[0];
    component.toggle(todo);

    expect(component.error).toBe('No se pudo cambiar el estado del todo');
    expect(component.loading()).toBeFalse();
  });

  it('applyFilters() sin cambios debe llamar searchTodos() sin filtros relevantes', () => {
    api.searchTodos.calls.reset();

    component.applyFilters();

    expect(api.searchTodos).toHaveBeenCalledTimes(1);
    const args = api.searchTodos.calls.mostRecent().args[0] || {};
    expect(args.q).toBeUndefined();
    expect(args.done).toBeUndefined();
  });

  it('applyFilters() debe trim()ear filterText y pasarlo como q', () => {
    api.searchTodos.calls.reset();

    component.filterText = '  pan  ';
    component.filterDone = 'all';

    component.applyFilters();

    const args = api.searchTodos.calls.mostRecent().args[0] || {};
    expect(args.q).toBe('pan');
    expect(args.done).toBeUndefined();
  });

  it('applyFilters() con filterDone="done" debe mapear done=true', () => {
    api.searchTodos.calls.reset();

    component.filterText = '';
    component.filterDone = 'done';

    component.applyFilters();

    const args = api.searchTodos.calls.mostRecent().args[0] || {};
    expect(args.done).toBeTrue();
  });

  it('applyFilters() con filterDone="pending" debe mapear done=false', () => {
    api.searchTodos.calls.reset();

    component.filterText = '';
    component.filterDone = 'pending';

    component.applyFilters();

    const args = api.searchTodos.calls.mostRecent().args[0] || {};
    expect(args.done).toBeFalse();
  });

  it('applyFilters() debe actualizar la lista de todos con el resultado del servicio', () => {
    component.filterText = 'algo';
    component.filterDone = 'done';

    component.applyFilters();

    const todos = component.todos();
    expect(todos.length).toBe(1);
    expect(todos[0].title).toBe('Filtrado');
  });

  it('applyFilters() debe dejar loading() en false al finalizar', () => {
    component.filterText = 'algo';
    component.applyFilters();

    expect(component.loading()).toBeFalse();
  });

  it('refresh() debe limpiar errores previos antes de volver a cargar', () => {
    component.error = 'Error previo';

    component.refresh();

    expect(component.error).toBeNull();
  });

  it('refresh() debe setear error si health() falla', () => {
    (api.health as jasmine.Spy).and.returnValue(
      throwError(() => new Error('fail')),
    );

    component.refresh();

    expect(component.error).toBe('No se pudo obtener el estado de la API');
  });

  it('refresh() debe setear error si listTodos() falla', () => {
    (api.listTodos as jasmine.Spy).and.returnValue(
      throwError(() => new Error('fail')),
    );

    component.refresh();

    expect(component.error).toBe('No se pudo obtener los todos');
  });
});
