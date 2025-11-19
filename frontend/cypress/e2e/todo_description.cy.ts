describe('Flujo de descripción en TODOs', () => {
  const title = 'Tarea con descripción E2E';
  const description = 'Descripción E2E de prueba';

  beforeEach(() => {
    cy.visit('/');
  });

  it('crea un todo con descripción y lo muestra en el listado', () => {
    // Completar título y descripción
    cy.get('[data-testid="new-todo-title"]').clear().type(title);
    cy.get('[data-testid="new-todo-description"]')
      .clear()
      .type(description);

    // Agregar
    cy.get('[data-testid="add-todo-button"]').click();

    // Ver en el listado
    cy.contains('li', title)
      .should('contain.text', title)
      .and('contain.text', description);

    // Ver que persiste después de recargar
    cy.reload();

    cy.contains('li', title)
      .should('contain.text', title)
      .and('contain.text', description);
  });
});
