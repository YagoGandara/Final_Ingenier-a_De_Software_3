import { computeAdvancedStats, classifyTitleLength } from './stats-utils';
import { Todo } from './api.service';

function makeTodo(partial: Partial<Todo>): Todo {
  return {
    id: partial.id ?? 1,
    title: partial.title ?? 'Tarea',
    done: partial.done ?? false,
    // description es opcional: string | undefined
    description: partial.description,
  };
}

describe('classifyTitleLength', () => {
  it('clasifica títulos cortos correctamente', () => {
    expect(classifyTitleLength('')).toBe('short');
    expect(classifyTitleLength('abc')).toBe('short');
    expect(classifyTitleLength('abcdefghij')).toBe('short'); // 10
  });

  it('clasifica títulos medianos correctamente', () => {
    expect(classifyTitleLength('abcdefghijk')).toBe('medium'); // 11
    expect(classifyTitleLength('a'.repeat(25))).toBe('medium');
  });

  it('clasifica títulos largos correctamente', () => {
    expect(classifyTitleLength('a'.repeat(26))).toBe('long');
  });
});

describe('computeAdvancedStats', () => {
  it('devuelve ceros para lista vacía', () => {
    const stats = computeAdvancedStats([]);
    expect(stats.total).toBe(0);
    expect(stats.done).toBe(0);
    expect(stats.pending).toBe(0);
    expect(stats.with_description).toBe(0);
    expect(stats.without_description).toBe(0);
    expect(stats.title_short).toBe(0);
    expect(stats.title_medium).toBe(0);
    expect(stats.title_long).toBe(0);
  });

  it('cuenta done vs pending', () => {
    const stats = computeAdvancedStats([
      makeTodo({ title: 'A', done: false }),
      makeTodo({ title: 'B', done: true }),
      makeTodo({ title: 'C', done: false }),
    ]);

    expect(stats.total).toBe(3);
    expect(stats.done).toBe(1);
    expect(stats.pending).toBe(2);
  });

  it('cuenta descripción vs vacío', () => {
    const stats = computeAdvancedStats([
      makeTodo({ title: 'A', description: undefined }),
      makeTodo({ title: 'B', description: '   ' }),
      makeTodo({ title: 'C', description: 'algo' }),
    ]);

    expect(stats.with_description).toBe(1);
    expect(stats.without_description).toBe(2);
  });

  it('cuenta longitudes de título', () => {
    const stats = computeAdvancedStats([
      makeTodo({ title: 'short' }),
      makeTodo({ title: 'a'.repeat(15) }),
      makeTodo({ title: 'a'.repeat(30) }),
    ]);

    expect(stats.title_short).toBe(1);
    expect(stats.title_medium).toBe(1);
    expect(stats.title_long).toBe(1);
  });

  it('smoke test mezclado', () => {
    const stats = computeAdvancedStats([
      makeTodo({ title: 'short 1', description: 'desc', done: false }),
      makeTodo({ title: 'short 2', description: undefined, done: true }),
      makeTodo({ title: 'medium title 123', description: 'algo', done: false }),
      makeTodo({
        title: 'this is a very very long title for a todo',
        description: undefined,
        done: true,
      }),
    ]);

    expect(stats.total).toBe(4);
    expect(stats.done).toBe(2);
    expect(stats.pending).toBe(2);

    expect(stats.with_description).toBe(2);
    expect(stats.without_description).toBe(2);

    expect(stats.title_short).toBe(2);
    expect(stats.title_medium).toBe(1);
    expect(stats.title_long).toBe(1);
  });
});
