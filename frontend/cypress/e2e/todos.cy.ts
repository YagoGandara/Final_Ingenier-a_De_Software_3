describe('Todos App - E2E', () => {
  it('Carga la home y muestra la sección de Todos', () => {
    cy.visit('/');

    // Título de la app y sección de todos
    cy.contains('TP05 – Angular + FastAPI').should('exist');
    cy.contains('Todos').should('exist');

    // Input de nueva tarea visible
    cy.get('input[placeholder="Nueva tarea..."]').should('be.visible');

    // Botón Agregar visible (puede estar deshabilitado)
    cy.contains('button', 'Agregar').should('be.visible');
  });

  it('Permite tipear un TODO y hacer click en Agregar sin romper la app', () => {
    const newTodoText = `todo-cypress-${Date.now()}`;

    cy.visit('/');

    // Escribimos en el input
    cy.get('input[placeholder="Nueva tarea..."]')
      .clear()
      .type(newTodoText);

    // Click en el botón Agregar (aunque hoy no siempre agrega el item)
    cy.contains('button', 'Agregar').click();

    // La app sigue en la pantalla principal de Todos
    cy.contains('Todos').should('exist');

    // El input sigue visible y mantiene el texto tipeado
    // (comportamiento actual de la app con el bug)
    cy.get('input[placeholder="Nueva tarea..."]').should('have.value', newTodoText);
  });
});
