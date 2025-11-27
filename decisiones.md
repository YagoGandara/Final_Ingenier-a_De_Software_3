# Decisiones técnicas – TP08 Docker + Coverage + E2E

Este documento resume **qué se hizo, por qué y cómo** se tomaron las decisiones técnicas al evolucionar la app de TP05/TP06/TP07 hacia el TP08 con:

- 2 imágenes Docker (API + WEB) desplegadas en Azure App Service (QA y PROD).
- Más reglas de negocio (títulos, descripciones, filtros, stats avanzados).
- Más tests unitarios (front + back), tests de integración y E2E (Cypress).
- Persistencia real de datos con SQLite en almacenamiento persistente del App Service.

---

## 1. Estrategia general de arquitectura

### 1.1. Frontend + Backend como dos contenedores

- Se decidió **separar físicamente** frontend y backend en **dos imágenes Docker**:
  - `todos-api`: FastAPI + SQLite.
  - `todos-web`: Angular 18 build estático.
- Motivos:
  - Reflejar una arquitectura realista (SPA + API independiente).
  - Permitir escalar y diagnosticar por separado front y back en Azure App Service.
  - Cumplir el requerimiento de la cátedra: *“Asegurarse que son 2 imágenes (back y front), esas 2 van a QA y a prod”*.

Las imágenes se construyen **una sola vez por commit** y se publican en Docker Hub con tag `$(Build.BuildId)` y `latest`. QA y PROD referencian **las mismas imágenes** → *build once, deploy many*.

### 1.2. Mismo artefacto para QA y PROD

- API y WEB se construyen una vez en el stage **Build** del pipeline.
- La diferencia entre QA y PROD se maneja únicamente con **variables de entorno** en cada Web App:
  - `APP_ENV`, `DB_URL` / `DATABASE_URL`, `API_BASE_URL`, etc.
- Beneficios:
  - Lo que se prueba en QA es exactamente lo que se despliega a PROD.
  - Se evita duplicar lógica de build por entorno y se simplifica el pipeline.

---

## 2. Base de datos

### 2.1. SQLite por entorno con persistencia real

Se eligió **SQLite** como motor de base de datos, con archivo **persistente** en:

```text
/home/data/app.db
```

dentro de cada Web App (contenedor).

**Motivos:**

- No generar costos adicionales (no se usa un servidor de DB administrado).
- Suficiente para el volumen y complejidad del TP.
- La carpeta `/home` en App Service se mantiene entre redeploys → la data no se pierde.
- Cada entorno (QA / PROD / local) tiene su archivo de DB independiente, aislado por host y volumen del contenedor.

### 2.2. Creación de tablas y seed

El ORM (SQLAlchemy) ejecuta `Base.metadata.create_all(bind=engine)` al iniciar la app, asegurando que la tabla `todos` exista antes de servir requests.

Se expone un endpoint de seed controlado:

- `POST /admin/seed` protegido con header `X-Seed-Token` + variable `SEED_TOKEN`.
- El seed no hace nada si la tabla ya tiene filas (**idempotente**).
- Se puede además activar `SEED_ON_START=true` en QA para acelerar pruebas automatizadas.
- Decisión: **no** autoseedear PROD para evitar modificaciones no controladas sobre datos reales.

### 2.3. Resolución de `DB_URL` / `DATABASE_URL`

La URL de SQLAlchemy se resuelve así:

```python
SQLALCHEMY_DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("DB_URL")
    or "sqlite:///./app.db"
)
```

- En QA/PROD se define `DB_URL=sqlite:////home/data/app.db`.
- En local/CI, si no hay variables, se usa `sqlite:///./app.db` (archivo junto a la app).
- Si la URL es SQLite con path absoluto, el backend se asegura de que el directorio exista antes de crear el engine.

---

## 3. Configuración de entorno

### 3.1. Backend – App Settings

Variables principales en la Web App de API (QA / PROD):

- `APP_ENV`: etiqueta de entorno (`qa`, `prod`, `local`) → se expone en `/admin/debug`.
- `DATABASEB_URL`: cadena SQLAlchemy, ej: `sqlite:////home/data/app.db`.
- `SEED_TOKEN`: secreto para `/admin/seed`.
- `SEED_ON_START`: `true` solo en QA si se desea seed automático.

**Decisión:** todo lo sensible (DB, CORS, seed) se define por configuración, sin re-compilar.

### 3.2. Frontend – `env.js` + `environment.ts`

El frontend obtiene la URL base de la API desde:

- `window.__env.apiBase` (objeto generado en `assets/env.js` en runtime, a partir de `API_BASE_URL` en la Web App), o
- `environment.apiBaseUrl` como fallback para desarrollo local.

El valor se normaliza para evitar dobles barras:

```ts
(window.__env?.apiBase || environment.apiBaseUrl || '').replace(/\/+$/, '')
```

**Decisión:** mantener un único build Angular y cambiar solo `env.js` por entorno, lo que simplifica CI/CD y asegura que QA y PROD usan exactamente la misma SPA.

---

## 4. Diseño del backend (FastAPI)

### 4.1. Separación de lógica de dominio

La lógica de negocio se concentra en `logic.py`:

- `normalize_title(text: str) -> str`
  - Hace trim y compacta espacios internos.
  - Evita considerar títulos distintos cadenas que visualmente son iguales.
- `validate_new_todo(title: str, existing_titles: list[str])`
  - Valida:
    - título no vacío,
    - títulos únicos (case-insensitive) sobre la lista existente.
- `filter_todos(todos, q: str | None, done: bool | None)`
  - Filtro por texto que busca en título y descripción.
  - Filtra por estado `done` si se indica.
- `compute_stats(todos)`
  - Calcula `total`, `done`, `pending`.

**Motivo:** hacer la lógica testeable de forma pura (sin HTTP ni DB) y reutilizable desde los endpoints.

### 4.2. Endpoints de negocio

- `POST /api/todos`:
  - Aplica `normalize_title` + `validate_new_todo`.
  - Persiste `title` normalizado y `description` opcional.
  - Respuestas relevantes:
    - `400` si el título está vacío (`title must not be empty`).
    - `400` si el título ya existe (`title must be unique`).

- `GET /api/todos/stats`:
  - Usa `compute_stats` para devolver resumen de tareas (hechas / pendientes / total).

- `GET /api/todos/search`:
  - Usa `filter_todos`:
    - `q` busca en título y descripción, case-insensitive.
    - `done` permite listar solo pendientes o solo hechas.

- `PATCH /api/todos/{id}/toggle`:
  - Invierte el campo `done`.
  - `404` si el `id` no existe.

### 4.3. Endpoints administrativos

- `/admin/debug`:
  - Devuelve:
    - `env`,
    - `db_url` efectivo,
    - `db_path`,
    - `db_file_exists` (booleano).
  - Se usa para diagnosticar problemas de configuración de DB y asegurar que se está usando `/home/data/app.db`.

- `/admin/touch`:
  - Devuelve `{"count": n}`.
  - Útil como smoke test de DB desde el pipeline o herramientas externas.

- `/admin/seed`:
  - Solo funciona si el `X-Seed-Token` coincide con `SEED_TOKEN`.
  - Permite poblar la DB con datos demo de forma controlada.

---

## 5. Diseño del frontend (Angular)

### 5.1. División de responsabilidades

**`ApiService`:**

- Encapsula el acceso HTTP:
  - `health()`, `listTodos()`, `addTodo()`, `stats()`, `searchTodos()`, `toggleTodo()`.
- Es el único lugar que conoce la URL base y rutas concretas.

**`AppComponent`:**

- Maneja el estado de la UI con signals:
  - `todos`, `stats`, `extendedStats`, `filters`, `health`, `loading`, `error`.
- Decide cuándo refrescar stats, aplicar filtros y mostrar mensajes.

Este patrón “servicio + componente” permite tests claros de API y de lógica de UI por separado.

### 5.2. Reglas de UI y negocio en el front

**Validación de título:**

- Si `newTitle` está vacío o son solo espacios → no llama al backend.
- Aplica `trim()` antes de construir el payload `{ title, description }`.

**Manejo de descripción:**

- El formulario incluye campo **Descripción (opcional)**.
- Si el usuario la completa, se envía al backend y se muestra debajo del título en la lista.
- En la UI se distingue entre todos “Con descripción” y “Sin descripción” en el resumen avanzado.

**Manejo de errores:**

- Si la API responde `400` por título duplicado, se muestra un mensaje específico:
  - “Ya existe una tarea con ese título”.
- Para otros errores (network, `500`, etc.) se muestra un mensaje genérico.
- Se utiliza una bandera `loading` para evitar dobles submits y acciones mientras hay requests en vuelo.

### 5.3. Filtros y resumen (básico y avanzado)

**Resumen básico:**

- Datos desde `GET /api/todos/stats`:
  - Total,
  - Pendientes,
  - Hechas.

**Filtros:**

- Input de texto (filtro por título o descripción).
- Select con opciones `Todas`, `Pendientes`, `Hechas`.

**Método `applyFilters()`:**

- Mapea el select a `done=true/false` o `null`.
- Llama a `ApiService.searchTodos(q, done)`.
- Actualiza `todos` y recalcula el resumen avanzado sobre la lista visible.

**Resumen avanzado (front):**

Calculado en el componente a partir de la lista actual:

- Cantidad de TODOs “Con descripción” y “Sin descripción”.
- Clasificación de títulos por longitud:
  - Cortos (≤10),
  - Medianos (11–25),
  - Largos (≥26).

Esta lógica se testea en los unit tests del componente y se valida indirectamente en los E2E.

---

## 6. Estrategia de testing

### 6.1. Backend – Unit tests (lógica pura)

Framework: **pytest**.

Se testea `logic.py` de forma aislada:

- Normalización del título (`normalize_title`).
- Validación de nuevos TODOs (`validate_new_todo`): éxito, vacío, duplicado.
- Filtrado (`filter_todos`) con combinaciones de `q` y `done` sobre título y descripción.
- Stats (`compute_stats`): distintos escenarios de hechos/pendientes.

**Decisión:** la lógica de dominio es donde están las reglas importantes, se garantiza buena cobertura y tests rápidos.

### 6.2. Backend – Tests de rutas

Se combinan dos enfoques:

1. **Override de dependencias / FakeStore:**
   - Se reemplaza la dependencia de almacenamiento (`Store`) por un fake en algunos tests.
   - Se verifica el contrato HTTP (status, body, mensajes de error) sin depender de SQLite.

2. **DB real para integración:**
   - Otros tests usan SQLite real de test.
   - Verifican wiring FastAPI + SQLAlchemy + rutas (incluidos endpoints de admin).

Casos cubiertos:

- `/healthz` (200 simple).
- `/api/todos` (listar + crear con/ sin descripción).
- Reglas de título vacío y duplicado.
- `/api/todos/stats` y `/api/todos/search` (contar y filtrar correctamente).
- `PATCH /api/todos/{id}/toggle` (cambio de `done` y `404` si no existe).
- `/admin/seed`, `/admin/touch`, `/admin/debug` en distintos escenarios.

### 6.3. Frontend – Unit tests

Framework: **Angular 18 + Karma + Jasmine**.

#### 6.3.1. `ApiService`

- Se usa `HttpClientTestingModule` + `HttpTestingController`.
- Se simula `window.__env = { apiBase: 'http://fake-api/' }`.
- Se verifica que:
  - `health()` haga `GET http://fake-api/healthz`.
  - `listTodos()` → `GET http://fake-api/api/todos`.
  - `addTodo()` → `POST http://fake-api/api/todos` con `{ title, description }`.
  - `stats()` → `GET /api/todos/stats`.
  - `searchTodos()` arme correctamente `q` y `done` en query params.
  - `toggleTodo(id)` → `PATCH http://fake-api/api/todos/{id}/toggle`.

#### 6.3.2. `AppComponent`

Se testeó la clase usando un stub de `ApiService` y *spies* de Jasmine.

Casos cubiertos:

- Carga inicial (`ngOnInit`): llama `health`, `listTodos`, `stats`.
- `add()`:
  - Ignora títulos vacíos o con solo espacios.
  - Aplica `trim()`.
  - Envía descripción si existe.
  - Agrega el TODO a `todos`.
  - Limpia `newTitle` / `newDescription`.
  - Cambia `loading` correctamente y maneja errores (incluyendo título duplicado).
  - Refresca `stats` con `ApiService.stats()`.
- `toggle()`:
  - Llama a `toggleTodo(id)`.
  - Actualiza el ítem en la lista.
  - Refresca `stats` y maneja error/loading.
- `applyFilters()`:
  - Mapea el filtro de UI a `done`.
  - Llama a `searchTodos()`.
  - Actualiza `todos`.
  - Recalcula el resumen avanzado (incluyendo métricas de descripción y longitud de título).

### 6.4. E2E – Cypress (Front + Back reales)

Herramienta: **Cypress 13**, modo `chrome --headless`.

Script `npm run e2e`:

- `ng serve` en <http://localhost:4200>.
- Cypress se ejecuta contra esa URL.

Requisito: API levantada en <http://localhost:8080> (el pipeline la levanta con `uvicorn` en background).

Escenarios principales:

- **Smoke:**
  - Verifica que la app Angular carga en `/` y que existe `<app-root>`.

- **Flows de TODOs:**
  - Crear un TODO con descripción:
    - El ítem aparece en el listado con título + descripción.
    - El formulario se limpia.
    - El resumen avanzado refleja que hay al menos un ítem “Con descripción”.
  - Crear un TODO sin descripción.
  - Toggle de estado (pendiente ↔ hecha).
  - Manejo de título duplicado, mostrando el mensaje de error correcto.

**Decisión:** en E2E se evita depender de deltas numéricos exactos en las stats porque la base puede tener datos previos; la lógica numérica ya está probada en unit/integración.

---

## 7. CI/CD – Azure DevOps + SonarCloud + Docker

### 7.1. Stage Build

Se ejecuta en cada push a `main`. Pasos principales:

**Preparar toolchains:**

- `NodeTool@0` (Node 20.x).
- `UsePythonVersion@0` (Python 3.12).

**SonarCloud Prepare:**

- Usa `sonar-project.properties`.
- Lee coverage:
  - Python: `backend/coverage.xml`.
  - TS/JS: `frontend/coverage/lcov.info`.
- Excluye `node_modules`, `dist`, `frontend/cypress`, `.spec.ts`.

**Backend:**

- `pip install -r requirements.txt`.
- `flake8 app`.
- `pytest --cov=app ...` genera `coverage.xml` y `TEST-backend.xml`.
- Se publican resultados y coverage como artefactos del build.

**Levantar API para Cypress:**

- `uvicorn app.main:app --host 0.0.0.0 --port 8080` en background.
- Loop de espera sobre `http://localhost:8080/healthz`.

**Frontend:**

- `npm ci` (fallback a `npm i --legacy-peer-deps` si hace falta).
- `npm run test:ci` → unit tests + coverage.
- Publicación de resultados JUnit y Cobertura.
- Limpieza de resultados viejos de Cypress.
- `npm run e2e` → Cypress contra `http://localhost:4200`.
- Publicación de resultados E2E JUnit.

**SonarCloud Analyze + Publish:**

- Ejecuta análisis.
- Quality Gate actúa como corte duro: si no pasa, no se despliega.

**Docker:**

- Build & push `todos-api` y `todos-web` a Docker Hub con tags `$(Build.BuildId)` y `latest`.

### 7.2. Stages DeployQA y DeployPROD

Ambos dependen de **Build** (`condition: succeeded()`).

**DeployQA:**

- **WebApp API QA:**
  - Usa imagen `todos-api:$(Build.BuildId)`.
  - App Settings: `APP_ENV=qa` (DB y otros se gestionan directo en el Web App).
- **WebApp WEB QA:**
  - Usa imagen `todos-web:$(Build.BuildId)`.
  - App Settings:
    - `APP_ENV=qa`.
    - `API_BASE_URL=$(apiBaseUrlQA)`.
- Opcional: smoke tests llamando a `/readyz`, `/healthz` y al index del front.

**DeployPROD:**

- Igual a QA pero con:
  - WebApps de PROD.
  - `APP_ENV=prod`.
  - `API_BASE_URL=$(apiBaseUrlPROD)`.
- Usa un Environment **PROD** con aprobación manual antes del despliegue.

---

## 8. CORS, seguridad y endpoints sensibles

- `CORS_ORIGINS` se define distinto por entorno para limitar el origen del front.
- `/admin/seed`:
  - Requiere token correcto.
  - No se expone desde el frontend.
- `/admin/debug`:
  - Muestra solo metadatos de configuración (no datos de negocio).
  - Se utiliza en operaciones / troubleshooting de DB.

**Decisión:** ofrecer herramientas operativas sin abrirlas a cualquier usuario de la SPA.

---

## 9. Justificación frente a los pedidos de la cátedra (TP08)

**“Poner más UnitTest”:**

- Backend:
  - Tests de lógica de dominio (`logic.py`).
  - Tests de rutas (incluyendo stats, search, toggle, seed, debug).
- Frontend:
  - Tests de `ApiService` (todas las llamadas HTTP).
  - Tests de `AppComponent` (alta, toggle, filtros, errores).
- Todo se ejecuta en el pipeline y falla el build si algo se rompe.

**“Poner una app un poco más compleja”:**

- Reglas nuevas:
  - Títulos normalizados y únicos (negocio realista).
  - Descripciones opcionales, usadas en filtros y en stats avanzadas.
  - Filtros combinados por estado + texto.
  - Resumen básico (stats backend) y resumen avanzado (stats frontend).
- La UI refleja esta complejidad con secciones de health, filtros, resumen y listado enriquecido.

**“Asegurarse que son 2 imágenes (back y front), esas 2 van a QA y a prod”:**

- El pipeline construye dos imágenes Docker desde la raíz del repo.
- Ambas se suben a Docker Hub.
- QA y PROD referencian exactamente esas mismas imágenes, cambiando solo configuración.

Con estas decisiones, el TP08 muestra una aplicación full-stack con lógica de negocio no trivial, buena cobertura de tests (unitarios, integración y E2E) y un pipeline de CI/CD profesional con Docker, SonarCloud y despliegue a QA/PROD en Azure App Service.
