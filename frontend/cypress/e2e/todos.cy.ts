describe('Todos App - E2E', () => {
  const getStatsText = () => {
    return cy
      .contains('h3', 'Resumen')
      .parent()
      .find('p')
      .invoke('text');
  };

  const expectStatsFormat = () => {
    return getStatsText().then((text) => {
      const match = text.match(
        /Total:\s*\d+\s*·\s*Pendientes:\s*\d+\s*·\s*Hechas:\s*\d+/
      );
      expect(match, `Formato inválido de estadísticas: "${text}"`).to.not.be
        .null;
    });
  };

  beforeEach(() => {
    cy.visit('/');
  });

  it('Carga la home y muestra la sección de Todos con resumen y filtros', () => {
    cy.contains('TP05 – Angular + FastAPI').should('exist');
    cy.contains('Todos').should('exist');
    cy.contains('Filtros').should('exist');

    // Resumen visible y con formato válido
    cy.contains('h3', 'Resumen').should('exist');
    expectStatsFormat();

    cy.get('input[placeholder="Nueva tarea..."]').should('be.visible');
    cy.contains('button', 'Agregar').should('be.visible');
  });

  it('Permite crear un TODO y mantiene el resumen consistente', () => {
    const todoText = `Tarea Cypress ${Date.now()}`;

    cy.get('input[placeholder="Nueva tarea..."]').clear().type(todoText);
    cy.contains('button', 'Agregar').click();

    // El item aparece en la lista
    cy.contains('ul li', todoText).should('exist');

    // El input se limpia
    cy.get('input[placeholder="Nueva tarea..."]').should('have.value', '');

    // El resumen sigue estando y con formato correcto
    cy.contains('h3', 'Resumen').should('exist');
    expectStatsFormat();
  });

  it('Permite togglear el estado de un TODO y cambia el texto del botón', () => {
    const todoText = `Toggle Cypress ${Date.now()}`;

    // Creamos un TODO controlado para este test
    cy.get('input[placeholder="Nueva tarea..."]').clear().type(todoText);
    cy.contains('button', 'Agregar').click();
    cy.contains('ul li', todoText).as('todoItem');

    // Inicialmente debe tener el botón "Marcar como hecha"
    cy.get('@todoItem').within(() => {
      cy.contains('button', 'Marcar como hecha').should('exist').click();
    });

    // Después del toggle, el botón debe cambiar a "Marcar como pendiente"
    cy.get('@todoItem').within(() => {
      cy.contains('button', 'Marcar como pendiente').should('exist');
    });

    // El resumen sigue estando y con formato correcto
    cy.contains('h3', 'Resumen').should('exist');
    expectStatsFormat();
  });

  it('Muestra un mensaje de error cuando se intenta crear un TODO duplicado', () => {
    const todoText = `Duplicado Cypress ${Date.now()}`;

    // Creamos el TODO por primera vez
    cy.get('input[placeholder="Nueva tarea..."]').clear().type(todoText);
    cy.contains('button', 'Agregar').click();
    cy.contains('ul li', todoText).should('exist');

    // Intentamos crearlo de nuevo con el mismo título
    cy.get('input[placeholder="Nueva tarea..."]').type(todoText);
    cy.contains('button', 'Agregar').click();

    // El front debe mostrar el mensaje específico
    cy.contains('.card.error', 'Ya existe una tarea con ese título').should(
      'exist',
    );
  });
});
