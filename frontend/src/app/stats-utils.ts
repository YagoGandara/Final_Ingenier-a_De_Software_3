import { Todo } from './api.service';

export type TitleLength = 'short' | 'medium' | 'long';

export interface AdvancedStats {
  total: number;
  done: number;
  pending: number;
  with_description: number;
  without_description: number;
  title_short: number;
  title_medium: number;
  title_long: number;
}

function normalizeTitle(title: string | undefined): string {
  return (title ?? '').trim();
}

export function classifyTitleLength(title: string): TitleLength {
  const norm = normalizeTitle(title);
  const length = norm.length;

  if (length <= 10) {
    return 'short';
  }
  if (length <= 25) {
    return 'medium';
  }
  return 'long';
}

export function computeAdvancedStats(todos: Todo[]): AdvancedStats {
  let total = 0;
  let done = 0;
  let pending = 0;

  let with_description = 0;
  let without_description = 0;

  let title_short = 0;
  let title_medium = 0;
  let title_long = 0;

  for (const todo of todos) {
    total++;

    if (todo.done) {
      done++;
    } else {
      pending++;
    }

    const desc = (todo.description ?? '').trim();
    if (desc.length > 0) {
      with_description++;
    } else {
      without_description++;
    }

    const kind = classifyTitleLength(todo.title);
    if (kind === 'short') {
      title_short++;
    } else if (kind === 'medium') {
      title_medium++;
    } else {
      title_long++;
    }
  }

  return {
    total,
    done,
    pending,
    with_description,
    without_description,
    title_short,
    title_medium,
    title_long,
  };
}
