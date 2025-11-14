describe('TP07 - Smoke E2E', () => {
  it('Carga la aplicación Angular en /', () => {
    cy.visit('/');

    // Verifica que el root component de Angular exista
    cy.get('app-root').should('exist');

    // Y que el body no esté vacío
    cy.get('body').then(($body) => {
      expect($body.text().trim().length).to.be.greaterThan(0);
    });
  });
});
