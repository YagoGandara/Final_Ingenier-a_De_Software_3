# Decisiones técnicas – TP08 Docker + Coverage + E2E

Este documento resume **qué se hizo, por qué y cómo** se tomaron las decisiones técnicas al evolucionar la app de TP05/TP06/TP07 hacia el TP08 con Docker, más lógica de negocio, más tests y un pipeline de CI/CD completo.

---

## 1. Estrategia general de arquitectura

### 1.1. Frontend + Backend como dos contenedores

- Se decidió **separar físicamente** frontend y backend en **dos imágenes Docker**:
  - `todos-api`: FastAPI + SQLite.
  - `todos-web`: Angular build estático.
- Motivos:
  - Reflejar una arquitectura realista (SPA + API independiente).
  - Permitir escalar por separado front y back en Azure App Service.
  - Cumplir explícitamente con el requerimiento de la cátedra: *“Asegurarse que son 2 imágenes (back y front), esas 2 van a QA y a prod”*.

Las dos imágenes se construyen **una sola vez por commit** y se publican en Docker Hub con tag `BuildId` y `latest`. QA y PROD referencian **las mismas imágenes**

### 1.2. Mismo artefacto para QA y PROD

- Tanto para API como para WEB, la estrategia es:
  - **Build once, deploy many**.
  - La diferencia entre QA y PROD se maneja **vía variables de entorno** del App Service (por ejemplo `API_BASE_URL`, `ENV`, `DB_URL`).
- Beneficios:
  - Lo que se prueba en QA es exactamente lo que se despliega a PROD.
  - Se simplifica el pipeline: no hay builds distintos por entorno.

---

## 2. Base de datos

### 2.1. SQLite por entorno

- Se eligió **SQLite** como motor de base de datos, con archivo persistido en `/home/data/app.db` dentro de cada Web App (contenedor).
- Motivos:
  - No generar costos extra de infraestructura (SQL Server, Postgres administrado, etc.).
  - Suficiente para el volumen y complejidad del TP.
- Cada entorno (QA/PROD/local) tiene su **archivo de DB independiente**, aislado por host y volumen de contenedor.

### 2.2. Creación de tablas y seed

- El ORM (SQLAlchemy) ejecuta `Base.metadata.create_all(bind=engine)` al iniciar la app.
- La carga de datos inicial no se hace automáticamente en PROD; se expone un endpoint de administración:

  - `POST /admin/seed` protegido por header `X-Seed-Token` y variable `SEED_TOKEN`.
  - El seed **no hace nada** si la tabla ya tiene filas, para evitar duplicados.
  - Esto permite correr el seed de manera controlada (por ejemplo, desde Postman o scripts de mantenimiento).

Decisión: **no autoseedear PROD** para evitar tocar datos de producción sin control; en QA se puede habilitar `SEED_ON_START` para acelerar pruebas.

---

## 3. Configuración de entorno

### 3.1. Backend – App Settings

Variables principales en App Service (API):

1. `ENV`: etiqueta de entorno (`qa`, `prod`, `local`), útil para logs y health.
2. `DB_URL`: cadena SQLAlchemy, por ejemplo `sqlite:////home/data/app.db`.
3. `CORS_ORIGINS`: lista de orígenes permitidos para el front (por entorno).
4. `SEED_TOKEN`: secreto para `/admin/seed`.
5. `SEED_ON_START`: flag para permitir seed automático al iniciar (sólo QA/staging).

Decisión: **todo comportamiento sensible (DB, CORS, seed) se controla por configuración**, sin re-build de imagen.

### 3.2. Frontend – `env.js` + environment.ts

- El frontend lee la base de la API desde:

  1. `window.__env.apiBase` (inyectado en `assets/env.js` en runtime).
  2. `environment.apiBaseUrl` como fallback para desarrollo local.

- El valor se normaliza para evitar dobles barras:

  ```ts
  (window.__env?.apiBase || environment.apiBaseUrl || '').replace(/\/+$/, '')
  ```

Decisiones:

- Mantener un único build de Angular y **cambiar sólo `env.js` por entorno** usando la variable `API_BASE_URL` en el contenedor.
- Esto simplifica el pipeline y permite pruebas E2E usando la misma imagen que se va a PROD.

---

## 4. Diseño del backend (FastAPI)

### 4.1. Separación de lógica de dominio

Se extrajo la lógica de negocio a un módulo dedicado (`logic.py`):

- `normalize_title(text: str) -> str`  
  - Quita espacios extra y hace trim, para evitar títulos “distintos” que son iguales visualmente.
- `validate_new_todo(title: str, existing_titles: list[str])`  
  - Regla “título no vacío” → excepción específica.
  - Regla “títulos únicos, case-insensitive” → excepción específica.
- `filter_todos(todos, q: str | None, done: bool | None)`  
  - Reutilizada por `/api/todos/search`.
- `compute_stats(todos)`  
  - Calcula `total`, `done`, `pending` a partir de la lista actual.

Motivo: poder testear la lógica de negocio **de forma pura** (sin DB ni HTTP) y reutilizarla en los endpoints.

### 4.2. Endpoints de negocio

- `POST /api/todos`
  - Usa `normalize_title` + `validate_new_todo` antes de persistir.
  - Evita TODOs vacíos o duplicados.
- `GET /api/todos/stats`
  - Usa `compute_stats` sobre los registros actuales.
  - Justifica tener un resumen en el front y tests de stats en backend.
- `GET /api/todos/search`
  - Aplica `filter_todos` a la lista en memoria:
    - `q` filtra por título/descripcion, case-insensitive.
    - `done` permite ver sólo pendientes o sólo hechos.
- `PATCH /api/todos/{id}/toggle`
  - Invierte el flag `done` y devuelve el TODO actualizado.
  - Facilita un flujo de negocio realista (marcar tareas como hechas) para tests E2E.

### 4.3. Endpoints administrativos

- `/admin/debug`:
  - Devuelve info sobre `DB_URL` y si el archivo de DB existe.
  - Decisión: incluir una herramienta de diagnóstico simple sin exponer datos sensibles.
- `/admin/touch`:
  - Devuelve `{"count": n}` con el total de TODOs.
  - Útil para health checks y verificación de que la DB responde.

---

## 5. Diseño del frontend (Angular)

### 5.1. División de responsabilidades

- `ApiService`:
  - Encapsula todas las llamadas HTTP a la API (`health`, `listTodos`, `addTodo`, `stats`, `searchTodos`, `toggleTodo`).
  - Es la única pieza que conoce la URL base y la forma exacta de los endpoints.
- `AppComponent`:
  - Se enfoca en **manejar estado y UX**:
    - signals para `todos`, `stats`, `filters`, `loading`, `error`.
    - Decide cuándo refrescar stats, qué mensaje mostrar, cómo mapear select a `done=true/false`.

Decisión: seguir el patrón “smart component + service” para que:
- el service sea fácil de testear con `HttpTestingController`,
- el componente tenga tests independientes, usando un stub de `ApiService`.

### 5.2. UX y reglas en el front

- Validación mínima del título en el componente:
  - Si `newTitle` está vacío o son sólo espacios, no se llama al service.
  - El título se trimea antes de enviar al backend.
- Manejo de errores:
  - Errores de red/500 se mapean a mensajes genéricos.
  - Status 400 con mensaje de título duplicado se muestra de forma específica (“Ya existe una tarea con ese título”). Se decidió no exponer el texto crudo del backend, sino un mensaje controlado.
- Refresh de stats:
  - Después de `add()` y `toggle()` el componente vuelve a llamar a `stats()`.
  - Decisión explícita: evitar mostrar números stale de resumen.

### 5.3. Filtros y resumen

- Se decidió incluir una sección de **“Resumen”** en el front:
  - Muestra `Total / Pendientes / Hechas`.
  - Tiene un formato fijo `Total: X · Pendientes: Y · Hechas: Z`, fácil para controlar en Cypress.
- Se agregó sección de **Filtros**:
  - Input de texto + select (Todas/Pendientes/Hechas).
  - Se consume el nuevo endpoint `/api/todos/search`.
  - Decisión: centralizar toda la lógica de filtrado en el backend para mantener la app realista (backend-driven).

---

## 6. Estrategia de testing

### 6.1. Backend – Unit tests (lógica pura)

- Framework: `pytest`.
- Se testea `logic.py` en forma aislada:
  - `normalize_title`: trimming, espacios internos, cadenas raras.
  - `validate_new_todo`: casos de éxito, título vacío, duplicado (case-insensitive).
  - `filter_todos`: combinaciones de `q` y `done`.
  - `compute_stats`: diferentes combinaciones de TODOs para comprobar `total`, `done`, `pending`.

Decisión: concentrar la lógica de negocio en funciones puras permite tests rápidos, robustos y fáciles de mantener.

### 6.2. Backend – Tests de rutas (con y sin DB real)

- Se usan dos estrategias:

  1. **FakeStore / override de dependencias**:
     - Para algunos tests se reemplaza el acceso a la DB con un `FakeStore` que implementa los métodos `list`, `add`, etc.
     - Se usa `app.dependency_overrides[...]` para inyectar el fake.
     - Permite testear la lógica HTTP (status codes, body) sin depender de la DB.

  2. **SQLite real para integración**:
     - Otros tests usan la configuración real de DB (SQLite en memoria o archivo de test).
     - Garantiza que el wiring ORM + FastAPI está bien armado.

- Casos cubiertos:
  - `/healthz` responde 200 con el payload esperado.
  - `/api/todos` GET devuelve la lista correcta.
  - `/api/todos` POST:
    - caso feliz,
    - título vacío (400),
    - título duplicado (400).
  - `/api/todos/stats` cuenta correctamente hechos/pendientes.
  - `/api/todos/search` respeta filtros.
  - `PATCH /api/todos/{id}/toggle` cambia `done` y responde 404 cuando corresponde.
  - `/admin/seed`:
    - 401 si el token no coincide,
    - caso exitoso mockeando la función de seed.

Decisión: mezclar unit e integración da buena cobertura sin perder velocidad en CI.

### 6.3. Frontend – Unit tests

- Framework: Angular 18 + Karma + Jasmine.

#### 6.3.1. `ApiService`

- Se usa `HttpClientTestingModule` + `HttpTestingController`.
- Se fuerza `window.__env.apiBase = 'http://fake-api/'` para simular el `env.js` del pipeline.
- Se verifica que:
  - `health()` haga `GET http://fake-api/healthz`.
  - `listTodos()` haga `GET http://fake-api/api/todos`.
  - `addTodo()` haga `POST` correcto.
  - `stats()`, `searchTodos()`, `toggleTodo()` llamen a los endpoints adecuados con query params correctos.

Decisión: Si cambia la ruta de la API, estos tests fallan y obligan a ajustar el servicio (contrato HTTP explícito).

#### 6.3.2. `AppComponent`

- Se testea la **clase** con un stub de `ApiService` (spies Jasmine).
- Casos cubiertos:
  - `ngOnInit/constructor` llama `health()`, `listTodos()` y `stats()` y carga estado inicial.
  - `add()`:
    - ignora títulos vacíos,
    - trim del título,
    - agrega el TODO a la lista,
    - limpia `newTitle`,
    - maneja `loading`/`error`,
    - hace refresh de stats.
  - `toggle()`:
    - llama al service,
    - actualiza la lista,
    - refresca stats,
    - maneja errores.
  - `applyFilters()`:
    - mapea el filtro de UI a `done=true/false`,
    - actualiza `todos` y `loading` en función de la respuesta.

Decisión: probar lógica de front sin depender de DOM, para tests rápidos y estables.

### 6.4. E2E – Cypress (Front + Back reales)

- Herramienta: Cypress 13 en modo `chrome --headless`.
- Scripts:
  - `npm run e2e`:
    - levanta `ng serve`,
    - corre Cypress contra `http://localhost:4200`.
- Requisito: API levantada en `http://localhost:8080` (en CI se levanta con `uvicorn` en background).

#### 6.4.1. Escenarios E2E

- `smoke.cy.ts`:
  - Verifica que Angular carga correctamente en `/`.

- `todos.cy.ts`:
  - Carga home, ve sección de Todos, filtros y card de Resumen.
  - Crear un TODO:
    - aparece en el listado,
    - el input se limpia,
    - el resumen sigue presente con formato válido.
  - Toggle:
    - el botón cambia de “Marcar como hecha” a “Marcar como pendiente”.
  - Título duplicado:
    - muestra mensaje de error “Ya existe una tarea con ese título”.

Decisión importante: **no** asertar deltas numéricos exactos (`before + 1`, etc.) en stats en E2E, porque:
- la DB puede tener datos previos,
- hay concurrencia de requests,
- eso vuelve los tests frágiles sin agregar valor real, dado que la lógica numérica ya está cubierta en backend unit/integración.

---

## 7. CI/CD – Azure DevOps + Sonar + Docker

### 7.1. Stage Build

- Se ejecuta en cada push a `main`.
- Pasos clave:
  1. Preparar toolchains (Node + Python).
  2. **Backend**: instalar deps, correr `flake8`, `pytest` con coverage, publicar resultados.
  3. Levantar API (uvicorn) en background para E2E.
  4. **Frontend**: `npm ci`, `npm run test:ci`, `npm run e2e` (Cypress).
  5. Ejecutar análisis de SonarCloud y Quality Gate.
  6. Construir y publicar imágenes Docker de API y WEB en Docker Hub.

Decisión: el stage `Build` es un **quality gate fuerte**. Si cualquiera de estas cosas falla (tests, coverage, Sonar), el pipeline no avanza a despliegue.

### 7.2. Stages DeployQA y DeployPROD

- Ambos stages dependen de que `Build` termine OK (`condition: succeeded()`).
- `DeployQA`:
  - Despliega la imagen `todos-api` a la Web App de API QA.
  - Despliega la imagen `todos-web` a la Web App de WEB QA.
  - Inyecta `APP_ENV=qa` y `API_BASE_URL` con la URL de la API QA.
  - Opcionalmente ejecuta smoke tests contra `readyz`, `healthz` y el front.
- `DeployPROD`:
  - Idéntico a QA pero apuntando a PROD.
  - Protegido por **aprobación manual** en el Environment `PROD`.
  - Reutiliza las mismas imágenes Docker (`BuildId`) ya verificadas en QA.

Decisión: mostrar explícitamente la **promoción de un mismo build** de QA a PROD con gate humano, como pide la cátedra.

---

## 8. CORS, seguridad y endpoints sensibles

- `CORS_ORIGINS` se configura distinto por entorno para restringir el origen del SPA.
- `/admin/seed`:
  - requiere `X-Seed-Token` correcto,
  - no expone interfaz en el frontend,
  - no hace nada si la tabla ya tiene datos.
- `/admin/debug`:
  - expone sólo información mínima de configuración (sin datos sensibles),
  - se usa para diagnosticar problemas de conexión a la DB o configuración de `DB_URL`.

Decisión: ofrecer herramientas de operación (seed/debug) sin exponerlas en la UI ni dejarlas totalmente abiertas.

---

## 9. Justificación frente a los pedidos hechos luego del TP08

1. **“Poner más UnitTest”**
   - Se agregaron tests unitarios de lógica de dominio en backend.
   - Se ampliaron los tests de rutas para cubrir reglas de negocio nuevas.
   - Se agregaron tests de servicio y componente en el frontend.
   - Todos los tests se ejecutan y publican en el pipeline, con falla dura si alguno falla.

2. **“Poner una app un poco más compleja”**
   - Se agregaron reglas de negocio reales:
     - títulos normalizados y únicos,
     - resumen de stats,
     - filtros de búsqueda,
     - toggle de estado.
   - El frontend refleja esta complejidad con filtros, resumen y manejo de errores.

3. **“Asegurarse de que son 2 imágenes (back y front), esas 2 van a QA y a prod”**
   - El pipeline construye dos imágenes Docker (API y WEB) y las publica en Docker Hub.
   - Las mismas imágenes se reutilizan en QA y PROD mediante Azure Web Apps para contenedores.
   - El cambio de entorno se hace por configuración (`APP_ENV`, `API_BASE_URL`), no por rebuild.
