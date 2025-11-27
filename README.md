# TP08 – Docker + Code Coverage + E2E (sobre TP05/TP06/TP07)

Aplicación TODO mínima pero **no trivial**, usada para:

- Practicar **CI/CD** con Azure DevOps.
- Desplegar **frontend + backend** en **Azure App Service (Linux, contenedores)** para QA y Producción.
- Agregar **reglas de negocio**, **tests unitarios**, **tests de integración** y **E2E (Cypress)**.
- Construir y publicar **2 imágenes Docker** (API y WEB) en Docker Hub; las mismas imágenes se usan en QA y PROD.
- Gestionar **persistencia real de datos** con SQLite en almacenamiento persistente del App Service.

La base original viene de los TP05/TP06/TP07 y se fue extendiendo en este repositorio.

---

## 1. Stack / Arquitectura

- **Frontend**: Angular 18 (SPA, proyecto `tp05-web`).
- **Backend**: FastAPI (Python 3.12).
- **DB**: SQLite por entorno.  
  - Local / CI: archivo `./app.db` en el contenedor.
  - QA/PROD: archivo **persistente** en `/home/data/app.db` dentro del App Service.
- **Infra**:
  - Azure Web Apps para contenedores (Linux, App Service Plan).
  - 2 WebApps por entorno: una para API y otra para WEB (QA y PROD).
- **CI/CD**:
  - Azure DevOps multi-stage (`azure-pipelines.yml`).
  - SonarCloud para análisis estático y coverage.
  - Docker Hub para publicar imágenes (`todos-api`, `todos-web`).
- **Healthchecks**:
  - `/`        → ping básico.
  - `/healthz` → liveness simple de la app.
  - `/readyz`  → ready + check de DB.

---

## 2. Funcionalidad de la aplicación

### 2.1. Backend (FastAPI)

**Endpoints principales:**

- `GET /`  
  Ping básico:

  ```json
  { "status": "ok", "message": "tp05-api running" }
  ```

- `GET /healthz`  
  Verifica que la app FastAPI esté viva.

- `GET /readyz`  
  Hace `SELECT 1` contra la DB; si falla devuelve `503`. Se usa en smoke tests/pipeline.

**Endpoints de TODOs**  
Cada TODO tiene:

```json
{
  "id":          "number",
  "title":       "string",
  "description": "string | null",
  "done":        "boolean"
}
```

- `GET /api/todos`  
  Lista todos los TODOs (ordenados por `id`).

- `POST /api/todos`  
  Crea un TODO con body:

  ```json
  { "title": "texto", "description": "opcional" }
  ```

  **Reglas de negocio:**

  - `title` se normaliza (trim + compactar espacios).
  - Si el título queda vacío → `400 {"detail": "title must not be empty"}`.
  - Títulos únicos, case-insensitive → `400 {"detail": "title must be unique"}`.
  - `description` es opcional; se guarda tal cual si viene.

- `GET /api/todos/stats`  
  Devuelve un resumen:

  ```json
  {
    "total":   0,
    "done":    0,
    "pending": 0
  }
  ```

  Calculado en `logic.compute_stats()` a partir del estado actual de la tabla.

- `GET /api/todos/search?q=<text>&done=<true|false>`  
  Filtra TODOs en memoria:

  - `q`: busca en título y descripción (case-insensitive).
  - `done`: filtra por estado (`true` → hechas, `false` → pendientes).
  - Si no se pasan filtros, devuelve la lista completa (equivalente a `/api/todos`).

- `PATCH /api/todos/{todo_id}/toggle`  
  Invierte el campo `done` del TODO:

  - `200` con el TODO actualizado si existe.
  - `404 {"detail": "todo not found"}` si el `id` no existe.

**Endpoints administrativos**

- `POST /admin/seed`  
  Cabezal `X-Seed-Token: <token>`:

  - Si el token coincide con `SEED_TOKEN` y la tabla está vacía, inserta datos de ejemplo.
  - Útil para ambientes de demo/QA.

- `GET /admin/debug`  
  Devuelve info de la DB efectiva que está usando la API:

  ```json
  {
    "env": "qa|prod|local",
    "db_url": "sqlite:////home/data/app.db",
    "db_path": "/home/data/app.db",
    "db_file_exists": true
  }
  ```

  Sirve para validar rápidamente:

  - qué `DB_URL`/`DATABASE_URL` se está tomando,
  - si el archivo de DB existe en el filesystem.

- `GET /admin/touch`  
  Devuelve `{"count": n}` con el total de registros (smoke test simple de DB).

---

### 2.2. Frontend (Angular)

Pantalla única (`AppComponent`), organizada en 3 secciones principales.

#### 2.2.1. Health

- Card que muestra el estado de `/healthz` (status + env).
- Se consulta al iniciar y en cada `refresh()`.

#### 2.2.2. Resumen y resumen avanzado

**Resumen básico:**

Muestra:

- Total
- Pendientes
- Hechas

Datos provenientes de `GET /api/todos/stats` (se refrescan al crear / togglear).

**Resumen avanzado:**

- “Con descripción” vs “Sin descripción”.
- Cantidad de títulos:
  - Cortos (≤10 chars),
  - Medianos (11–25),
  - Largos (≥26).

Todo se calcula en el frontend a partir de la lista actual de TODOs.

#### 2.2.3. Filtros

- Input de texto: filtra por título o descripción.
- Select: `Todos | Pendientes | Hechos`.
- Botón “Aplicar filtros”:
  - Internamente mapea a parámetros `q` y `done`.
  - Llama a `GET /api/todos/search`.
  - Actualiza la lista y el resumen avanzado (porque se basa en la lista visible).

#### 2.2.4. Todos

**Form de alta:**

- Input “Nueva tarea…” (título).
- Textarea “Descripción (opcional)”.
- Botón Agregar.

**Comportamiento:**

- Si el título está vacío o son solo espacios, **no** hace request.
- Hace `trim()` del título.
- Llama a `POST /api/todos` con `{ title, description }`.
- Al éxito:
  - Inserta el TODO devuelto al principio de la lista.
  - Limpia los campos de título y descripción.
  - Refresca el resumen básico y avanzado.

**Manejo de errores:**

- Si la API devuelve `400 title must be unique`, se muestra un mensaje específico:
  - “Ya existe una tarea con ese título”.
- Cualquier otro error se muestra como error genérico en la UI.

**Listado de TODOs:**

Cada item muestra:

- Ícono:
  - ⏳ para pendientes.
  - ✔️ para hechas.
- Título.
- Descripción (si existe), en una línea abajo del título.
- Botón por item:
  - “Marcar como hecha” / “Marcar como pendiente” → `PATCH /api/todos/{id}/toggle`.
  - Actualiza la lista y el resumen.

**Manejo de estados:**

- Se usa una bandera `loading` para deshabilitar acciones mientras hay requests activos.
- Los errores se muestran en una card roja en la parte inferior.

---

## 3. Ejecución local

### 3.1. Local con Docker (recomendado)

En la raíz del repo:

```bash
docker compose down -v
docker compose build
docker compose up
```

Servicios:

- Frontend: <http://localhost:4200>
- API: <http://localhost:8080>

Tests del backend con Docker:

```bash
docker compose run --rm api-tests
```

### 3.2. Local “puro” (sin Docker)

**Backend**

```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

La API queda escuchando en <http://localhost:8080>.

**Frontend**

```bash
cd frontend
npm ci          # o npm install
npm start       # ng serve --host 0.0.0.0 --port 4200
```

La SPA queda en <http://localhost:4200> y consume la API local (`environment.apiBaseUrl = http://localhost:8080`).

---

## 4. Configuración por entorno

### 4.1. API – App Settings (QA | PROD)

Variables típicas en Azure Web App (API):

| Nombre       | Valor             | Descripción                                    |
|--------------|-------------------|-----------------------------------------------|
| `ENV`        | `qa` / `prod`     | etiqueta de entorno (se muestra en debug)     |
| `API_PORT`   | `8080`            | puerto de uvicorn                             |
| `DB_URL`     | `sqlite:////home/data/app.db` | DB SQLite persistente en almacenamiento `/home` |
| `CORS_ORIGINS` | `<URL del Front>` | ej: `https://web-...azurewebsites.net`       |
| `SEED_TOKEN` | `<secreto>`       | token para `/admin/seed`                      |
| `SEED_ON_START` | `false` / `true` | si hace seed automáticamente                 |

En el código, la URL se resuelve como:

```python
SQLALCHEMY_DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("DB_URL")
    or "sqlite:///./app.db"
)
```

- En QA/PROD se usa `DB_URL` (y opcionalmente `DATABASE_URL` si se define).
- En local/CI, si no hay vars, usa `sqlite:///./app.db`.
- Si la URL es SQLite con path absoluto (`sqlite:////home/data/app.db`), la app se asegura de que el directorio exista antes de crear el engine.
- El container crea las tablas al iniciar:

```python
Base.metadata.create_all(bind=engine)
```

### 4.2. Front – Inyección de URL de API

El front está preparado para leer la URL de la API desde:

- `window.__env.apiBase` (archivo `assets/env.js` generado en tiempo de build), o
- `environment.apiBaseUrl` (valor por defecto para desarrollo local).

Ejemplo de `env.js`:

```js
window.__env = { apiBase: "https://tp07-todos-api-qa-cont-...azurewebsites.net" };
```

El código Angular toma:

```ts
(window.__env?.apiBase || environment.apiBaseUrl || '').replace(/\/+$/, '')
```

De forma que el mismo build funciona en local, QA y PROD sin re-compilar.

En el pipeline de despliegue, el WebApp de frontend recibe en App Settings:

- `APP_ENV=qa|prod`
- `API_BASE_URL=$(apiBaseUrlQA|apiBaseUrlPROD)`

El `Dockerfile.prod` del frontend genera `assets/env.js` en base a `API_BASE_URL`.

---

## 5. Testing

### 5.1. Backend – Unit + Integración (pytest)

Comandos:

```bash
cd backend
pytest
# o con coverage explícito:
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html
```

**Tipos de tests:**

- `tests/test_logic.py`
  - `normalize_title` (trimming + espacios internos).
  - `validate_new_todo` (empty / duplicate).
  - `filter_todos` (texto + estado, usando título + descripción).
  - `compute_stats` (total/pending/done).

- `tests/test_todos_routes.py`
  - `/healthz`.
  - `/api/todos` (listar + crear con y sin descripción).
  - Reglas de título vacío y duplicado.
  - Que la descripción se persista correctamente.

- `tests/test_todos_extra_routes.py`
  - `/api/todos/stats` (contar hechos/pendientes).
  - `/api/todos/search` (`done`, `q`, combinaciones sobre título+descripción).
  - `POST /api/todos` usando título normalizado.
  - `PATCH /api/todos/{id}/toggle` (cambio de `done` y 404).

Otros tests de integración verifican que los endpoints de admin (`/admin/seed`, `/admin/touch`) funcionen.

En el pipeline, `pytest` genera `coverage.xml` y `TEST-backend.xml` (JUnit) que se publican en Azure DevOps y se usan en SonarCloud.

### 5.2. Frontend – Unit (Karma/Jasmine)

Comando:

```bash
cd frontend
npm run test:ci
# ng test --watch=false --browsers=ChromeHeadless --code-coverage --karma-config=karma.conf.ci.js
```

Karma genera:

- `frontend/test-results/unit-tests.xml` (JUnit para Azure DevOps).
- `frontend/coverage/lcov.info` y `frontend/coverage/cobertura.xml` (para Sonar y Code Coverage).

**Tests cubren:**

- `src/app/api.service.spec.ts`:
  - Usa `HttpClientTestingModule` + `HttpTestingController`.
  - Verifica que:
    - `health()` llame a `GET /healthz` usando `window.__env.apiBase` normalizado.
    - `listTodos()` llame a `GET /api/todos`.
    - `addTodo()` haga `POST /api/todos` con `{ title, description }`.
    - `stats()` llame a `GET /api/todos/stats`.
    - `searchTodos()` arme correctamente `q` y `done` en los query params.
    - `toggleTodo()` llame a `PATCH /api/todos/{id}/toggle`.

- `src/app/app.component.spec.ts`:
  - En el `ngOnInit` se llama a `health()`, `listTodos()` y `stats()` y se carga el estado inicial.
  - `add()`:
    - No llama al servicio si `newTitle` está vacío o son solo espacios.
    - Hace `trim()` del título.
    - Envía descripción opcional si se completó.
    - Inserta el TODO en el array, limpia `newTitle` y `newDescription`.
    - Maneja `loading` y errores de título duplicado.
    - Refresca `stats` (`ApiService.stats()`).
  - `toggle()`:
    - Llama a `ApiService.toggleTodo(id)`.
    - Actualiza el TODO en la lista.
    - Refresca `stats`.
    - Maneja error y `loading`.
  - `applyFilters()`:
    - Mapea el select a `done=true/false`.
    - Llama a `searchTodos()` con filtros de texto+estado.
    - Actualiza `todos` y `loading`.
  - Se validan también los cálculos del resumen avanzado (con descripción / sin descripción, títulos cortos/medios/largos) a partir de la lista de TODOs.

### 5.3. E2E – Cypress

Comando:

```bash
cd frontend
npm run e2e
```

Este script:

- Hace `ng serve` en <http://localhost:4200>.
- Corre `cypress run --browser chrome --headless`.

Importante: Para que Cypress funcione, la API debe estar levantada en <http://localhost:8080>.  
En CI se levanta con `uvicorn` en background antes de ejecutar `npm run e2e`.

**Specs principales:**

- `cypress/e2e/smoke.cy.ts`:
  - Verifica que la aplicación Angular carga en `/`.

- `cypress/e2e/todos.cy.ts`:
  - La home muestra título, sección de Todos, filtros, resumen y resumen avanzado.
  - Crear un TODO con descripción:
    - El ítem aparece en la lista con título + descripción.
    - El input y textarea se limpian.
    - El resumen avanzado refleja correctamente “Con descripción”.
  - Crear un TODO sin descripción (para cubrir ambos casos).
  - Toggle:
    - El botón cambia de “Marcar como hecha” a “Marcar como pendiente”.
    - El resumen básico se mantiene consistente.
  - Duplicado:
    - Muestra el mensaje de error “Ya existe una tarea con ese título”.

En CI, los resultados de Cypress se guardan en `frontend/cypress/results/*.xml` y se publican como test run “Frontend E2E tests”.

---

## 6. CI/CD – Azure DevOps + Docker

Archivo principal: `azure-pipelines.yml`.

### 6.1. Stage Build

Se dispara en cada push a `main`.

**Job `build_and_analyze`:**

**Toolchains**

- Node 20.x (`NodeTool@0`).
- Python 3.12 (`UsePythonVersion@0`).

**SonarCloud Prepare**

- Usa `sonar-project.properties`.
- Reportes de coverage:
  - Python: `backend/coverage.xml`.
  - JS/TS: `frontend/coverage/lcov.info`.
- Excluye `node_modules`, `dist`, `frontend/cypress` y `.spec.ts`.

**Backend**

- `pip install -r requirements.txt`.
- `flake8 app` (análisis estático).
- `pytest` con coverage + JUnit.
- Publica resultados y coverage en Azure DevOps.

**Levantar API para E2E**

- `uvicorn app.main:app --host 0.0.0.0 --port 8080` en background.
- Bucle que espera a que `http://localhost:8080/healthz` responda.

**Frontend**

- `npm ci` (fallback a `npm i --legacy-peer-deps` si hace falta).
- `npm run test:ci` (unit tests + coverage).
- Publica `test-results/*.xml` como “Frontend unit tests”.
- Publica `coverage/cobertura.xml` como coverage de frontend.
- Limpia resultados viejos de Cypress.
- `npm run e2e` (Cypress contra la API levantada).
- Publica `frontend/cypress/results/*.xml` como “Frontend E2E tests”.

**SonarCloud Analyze + Publish**

- Ejecuta análisis y Quality Gate (falla el build si no pasa).

**Docker Build & Push**

- Imagen API:
  - `$(dockerHubNamespace)/todos-api:$(Build.BuildId)` y `:latest`.
  - Dockerfile: `backend/Dockerfile`.
- Imagen WEB:
  - `$(dockerHubNamespace)/todos-web:$(Build.BuildId)` y `:latest`.
  - Dockerfile: `frontend/Dockerfile.prod`.

Resultado: si algo de tests/coverage/Sonar falla, **no** se publican imágenes en Docker Hub.

### 6.2. Stage DeployQA (Containers)

- `dependsOn: Build`
- `condition: succeeded()`
- Usa environment **QA** en Azure DevOps.

**Pasos:**

- **API QA** (`AzureWebAppContainer@1`)
  - WebApp configurada para contenedores.
  - Imagen: `yagogandara/todos-api:$(Build.BuildId)`.
  - `APP_ENV=qa` (el resto de variables se gestionan directo en el Web App).

- **WEB QA**
  - Imagen: `yagogandara/todos-web:$(Build.BuildId)`.
  - App Settings:
    - `APP_ENV=qa`.
    - `API_BASE_URL=$(apiBaseUrlQA)` (URL de la API QA).

- **Smoke tests QA** (controlados por `runSmokeTests`):
  - Polling de `$(apiBaseUrlQA)readyz`.
  - Check de `$(apiBaseUrlQA)healthz`.
  - Check de `$(webBaseUrlQA)` (index del front).

### 6.3. Stage DeployPROD (Containers)

- `dependsOn: DeployQA`
- `condition: succeeded()`
- Environment **PROD** configurado con aprobación manual.

**Pasos análogos a QA:**

- **API PROD:**
  - Imagen: `yagogandara/todos-api:$(Build.BuildId)`.
  - `APP_ENV=prod`.

- **WEB PROD:**
  - Imagen: `yagogandara/todos-web:$(Build.BuildId)`.
  - `APP_ENV=prod`.
  - `API_BASE_URL=$(apiBaseUrlPROD)`.

- **Smoke tests PROD** (opcionales):
  - Poll a `healthz` y al front.

---

## 7. Troubleshooting rápido

- **Front no llega a la API:**
  - Revisar `API_BASE_URL` en App Settings del front.
  - Ver `/healthz` y `/readyz` en la API.

- **DB no persiste entre deploys:**
  - Ver `/admin/debug` → confirmar `db_url = sqlite:////home/data/app.db`.
  - Asegurarse de que no se esté usando `sqlite:///./app.db` en QA/PROD.

- **Cypress falla en CI:**
  - Verificar que el paso “Start backend API for Cypress” no falló.
  - Revisar `uvicorn.log` en el agente.

Este README resume la arquitectura, el flujo de CI/CD y cómo se testea y despliega la app full-stack (Angular + FastAPI + SQLite) con cobertura, análisis estático y E2E, incluyendo la persistencia real de datos entre despliegues.
