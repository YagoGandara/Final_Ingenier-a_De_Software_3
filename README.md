# TP08 – Docker + Code Coverage + E2E (sobre TP05/TP06/TP07)

Aplicación TODO mínima pero **no trivial**, usada para:

- Practicar **CI/CD** con Azure DevOps.
- Desplegar **frontend + backend** en **Azure App Service (Linux, contenedores)** para QA y Producción.
- Agregar **reglas de negocio**, **tests unitarios**, **tests de integración** y **E2E (Cypress)**.
- Construir y publicar **2 imágenes Docker** (API y WEB) en Docker Hub; las mismas imágenes se usan en QA y PROD.

La base original viene de los TP05/TP06/TP07 y se fue extendiendo en este repositorio.

---

## 1. Stack / Arquitectura

- **Frontend**: Angular 18 (SPA, proyecto `tp05-web`).
- **Backend**: FastAPI (Python 3.12).
- **DB**: SQLite por entorno (persistencia en `/home/data/app.db` dentro del container).
- **Infra**:
  - Azure Web Apps para contenedores (Linux, App Service Plan).
  - 2 WebApps: una para API y otra para WEB, tanto en QA como en PROD.
- **CI/CD**:
  - Azure DevOps multi-stage (`azure-pipelines.yml`).
  - SonarCloud para análisis estático y coverage.
  - Docker Hub para publicar imágenes (`todos-api`, `todos-web`).
- **Healthchecks**:
  - `/`        → ping básico.
  - `/healthz` → liveness simple de la app.
  - `/readyz` → ready + check de DB.

---

## 2. Funcionalidad de la aplicación

### 2.1. Backend (FastAPI)

Endpoints principales:

- `GET /`  
  Ping básico: `{"status": "ok", "message": "tp05-api running"}`.

- `GET /healthz`  
  Verifica que la app FastAPI esté viva.

- `GET /readyz`  
  Hace `SELECT 1` contra la DB; si falla devuelve 503, se usa en smoke tests/pipeline.

Endpoints de TODOs:

- `GET /api/todos`  
  Lista todos los TODOs (ordenados por `id`).

- `POST /api/todos`  
  Crea un TODO con body:

```json
{ "title": "texto", "description": "opcional" }
```

  Reglas de negocio:
  - `title` se normaliza (trim + compactar espacios).
  - Si el título queda vacío → **400** `{"detail": "title must not be empty"}`.
  - Títulos únicos, case-insensitive → **400** `{"detail": "title must be unique"}`.

- `GET /api/todos/stats`  
  Devuelve:

```json
{
  "total":   <int>,
  "done":    <int>,
  "pending": <int>
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
  - `404 {"detail": "todo not found"}` si `id` no existe.

Endpoints administrativos:

- `POST /admin/seed`  
  Cabezal `X-Seed-Token: <token>`:
  - Si el token coincide con `SEED_TOKEN` y la tabla está vacía, inserta datos de ejemplo.

- `GET /admin/debug`  
  Devuelve `db_url` y si existe el archivo de DB (ayuda para troubleshooting de `DB_URL`).

- `GET /admin/touch`  
  Devuelve `{"count": n}` con el total de registros.

### 2.2. Frontend (Angular)

Pantalla única (`AppComponent`):

- **Health**: muestra el estado de `/healthz` (status + env).
- **Resumen**:
  - Card con: `Total`, `Pendientes`, `Hechas`.
  - Datos provenientes de `GET /api/todos/stats` (se refrescan al crear / togglear).
- **Filtros**:
  - Input de texto: filtra por título/descripcion.
  - Select: `Todas | Pendientes | Hechas`.
  - Botón **“Aplicar filtros”** → usa `GET /api/todos/search`.
- **Todos**:
  - Input “Nueva tarea…” y botón **Agregar**:
    - Hace `POST /api/todos`.
    - Limpia el input al éxito.
    - Si el título ya existe, muestra error: “Ya existe una tarea con ese título”.
  - Listado con ícono:
    - ⏳ para pendientes.
    - ✔️ para hechas.
  - Botón por item:
    - “Marcar como hecha” / “Marcar como pendiente” → `PATCH /api/todos/{id}/toggle`.
    - Refresca también las estadísticas.

Manejo de errores:

- Si fallan `health`, `listTodos` o `stats`, se setea un mensaje de error en una card roja.
- Si fallan `add`, `toggle` o `search`, se muestran mensajes específicos.

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

- Frontend: `http://localhost:4200`
- API: `http://localhost:8080`

Tests del backend con Docker:

```bash
docker compose run --rm api-tests
```

---

### 3.2. Local “puro” (sin Docker)

#### Backend

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

La API queda escuchando en `http://localhost:8080`.

#### Frontend

```bash
cd frontend
npm ci          # o npm install
npm start       # ng serve --host 0.0.0.0 --port 4200
```

La SPA queda en `http://localhost:4200` y consume la API local (`environment.apiBaseUrl = http://localhost:8080`).

---

## 4. Configuración por entorno

### 4.1. API – App Settings (QA | PROD)

Variables típicas en Azure Web App (API):

| Nombre          | Valor                           | Descripción                            |
|-----------------|---------------------------------|----------------------------------------|
| `ENV`           | `qa` / `prod`                   | etiqueta de entorno                    |
| `API_PORT`      | `8080`                          | puerto de uvicorn                      |
| `DB_URL`        | `sqlite:////home/data/app.db`   | DB SQLite persistente                  |
| `CORS_ORIGINS`  | `<URL del Front>`               | ej: `https://web-...azurewebsites.net` |
| `SEED_TOKEN`    | `<secreto>`                     | token para `/admin/seed`               |
| `SEED_ON_START` | `false` / `true`                | si hace seed automáticamente           |

El container crea las tablas al iniciar:

```python
Base.metadata.create_all(bind=engine)
```

---

### 4.2. Front – Inyección de URL de API

El front está preparado para leer la URL de la API desde:

1. `window.__env.apiBase` (archivo `assets/env.js` montado/inyectado en runtime), ó
2. `environment.apiBaseUrl` (valor por defecto para desarrollo local).

En los contenedores de QA/PROD se usa un `env.js` generado a partir de `API_BASE_URL`:

```js
window.__env = { apiBase: "<URL de la API del entorno>" };
```

El código Angular toma:

```ts
(window.__env?.apiBase || environment.apiBaseUrl || '').replace(/\/+$/, '')
```

de forma que el mismo build funciona en local, QA y PROD.

En el pipeline de despliegue, el WebApp de frontend recibe en `App Settings`:

- `APP_ENV=qa|prod`
- `API_BASE_URL=<url de la API QA/PROD>`

El Dockerfile del frontend genera `assets/env.js` en base a `API_BASE_URL`.

---

## 5. Testing

### 5.1. Backend – Unit + Integración (pytest)

Comando:

```bash
cd backend
pytest
# o con coverage:
pytest --cov=app --cov-report=xml:coverage.xml --cov-report=html
```

Tipos de tests:

- `tests/test_logic.py`
  - `normalize_title` (trimming + espacios internos).
  - `validate_new_todo` (empty / duplicate).
  - `filter_todos` (texto + estado).
  - `compute_stats` (total/pending/done).
- `tests/test_todos_routes.py`
  - `/healthz`
  - `/api/todos` (listar + crear).
  - Reglas de título vacío y duplicado.
  - `/admin/seed` con token válido / inválido (seed mockeado).
- `tests/test_todos_extra_routes.py`
  - `/api/todos/stats` (contar hechos/pendientes).
  - `/api/todos/search` (done, q, combinaciones).
  - `POST /api/todos` usando título normalizado.
  - `PATCH /api/todos/{id}/toggle` (cambio de `done` y 404).

En el pipeline, `pytest` genera `coverage.xml` y `TEST-backend.xml` (JUnit) que se publican en Azure DevOps.

---

### 5.2. Frontend – Unit (Karma/Jasmine)

Comando:

```bash
cd frontend
npm run test:ci
# equivalente a ng test --watch=false --browsers=ChromeHeadless + cobertura
```

Tests:

- `src/app/api.service.spec.ts`
  - Usa `HttpClientTestingModule` + `HttpTestingController`.
  - Verifica que:
    - `health()` llame a `GET /healthz` usando `window.__env.apiBase` normalizado.
    - `listTodos()` llame a `GET /api/todos`.
    - `addTodo()` haga `POST /api/todos` con `{ title }`.
    - `stats()` llame a `GET /api/todos/stats`.
    - `searchTodos()` arme correctamente `q` y `done` en los query params.
    - `toggleTodo()` llame a `PATCH /api/todos/{id}/toggle`.

- `src/app/app.component.spec.ts`
  - Constructor llama `health()`, `listTodos()` y `stats()` y carga estado inicial.
  - `add()`:
    - No llama al servicio si `newTitle` está vacío o son sólo espacios.
    - Hace `trim()` del título y llama a `ApiService.addTodo()`.
    - Agrega el TODO al array, limpia `newTitle`, maneja `loading`.
    - Diferencia entre error genérico y título duplicado.
    - Refresca stats (`ApiService.stats()`).
  - `toggle()`:
    - Llama a `ApiService.toggleTodo(id)`.
    - Actualiza el TODO en la lista.
    - Refresca stats.
    - Maneja error y `loading`.
  - `applyFilters()`:
    - Mapea el select a `done=true/false`.
    - Llama a `searchTodos()` con filtros.
    - Actualiza `todos` y `loading`.
  - Manejo de error en `refresh()` si fallan `health()` o `listTodos()`.

---

### 5.3. E2E – Cypress

Comando:

```bash
cd frontend
npm run e2e
```

Este script:

1. Hace `ng serve` en `http://localhost:4200`.
2. Corre `cypress run --browser chrome --headless`.

> **Importante:** Para que Cypress funcione, la API debe estar levantada en `http://localhost:8080`.  
> En CI se levanta con `uvicorn` en background antes de ejecutar `npm run e2e`.

Specs:

- `cypress/e2e/smoke.cy.ts`
  - Smoke: verifica que la aplicación Angular carga en `/`.

- `cypress/e2e/todos.cy.ts`
  - La home muestra título, sección de Todos, filtros y card de Resumen.
  - Crear un TODO:
    - El ítem aparece en la lista.
    - El input se limpia.
    - El resumen sigue presente y con formato válido.
  - Toggle:
    - El botón cambia de “Marcar como hecha” a “Marcar como pendiente”.
    - El resumen se mantiene consistente.
  - Duplicado:
    - Muestra el mensaje de error “Ya existe una tarea con ese título”.

---

## 6. CI/CD – Azure DevOps + Docker

Archivo: `azure-pipelines.yml`.

### 6.1. Stage `Build`

- Se dispara en cada push a `main`.
- Job `build_and_analyze`:
  1. **Toolchains**
     - Node 20.x (`NodeTool@0`).
     - Python 3.12 (`UsePythonVersion@0`).
  2. **SonarCloud Prepare**
     - Usa `sonar-project.properties`.
     - Reportes de coverage:
       - Python: `backend/coverage.xml`.
       - JS/TS: `frontend/coverage/lcov.info`.
  3. **Backend**
     - `pip install -r requirements.txt`.
     - `flake8 app` (análisis estático).
     - `pytest` con coverage + JUnit.
     - Publica resultados y coverage en Azure DevOps.
  4. **Levantar API para E2E**
     - `uvicorn app.main:app --host 0.0.0.0 --port 8080` en background.
  5. **Frontend**
     - `npm ci` (fallback `npm i` si hace falta).
     - `npm run test:ci` (unit tests + coverage).
     - `npm run e2e` (Cypress contra la API levantada).
     - Publica coverage de frontend (`cobertura.xml`).
  6. **SonarCloud Analyze + Publish**
     - Ejecuta análisis y Quality Gate (falla el build si no pasa).
  7. **Docker Build & Push**
     - Imagen API:
       - `$(dockerHubNamespace)/todos-api:$(Build.BuildId)` y `:latest`.
       - Dockerfile: `backend/Dockerfile`.
     - Imagen WEB:
       - `$(dockerHubNamespace)/todos-web:$(Build.BuildId)` y `:latest`.
       - Dockerfile: `frontend/Dockerfile.prod`.

Resultado: si algo de tests/coverage/Sonar falla, **no se construyen ni publican imágenes**.

---

### 6.2. Stage `DeployQA` (Containers)

- `dependsOn: Build`
- `condition: succeeded()`

Pasos:

1. **API QA** (`AzureWebAppContainer@1`)
   - WebApp de Azure configurada para contenedores.
   - Imagen: `yagogandara/todos-api:$(Build.BuildId)`.
   - App Settings:
     - `APP_ENV=qa`.

2. **WEB QA**
   - Imagen: `yagogandara/todos-web:$(Build.BuildId)`.
   - App Settings:
     - `APP_ENV=qa`.
     - `API_BASE_URL=$(apiBaseUrlQA)`.

3. **Smoke tests QA** (opcional, por variable `runSmokeTests`)
   - Hace polling de `$(apiBaseUrlQA)readyz`.
   - Chequea `$(apiBaseUrlQA)healthz`.
   - Chequea que `$(webBaseUrlQA)` responda.

---

### 6.3. Stage `DeployPROD` (Containers)

- `dependsOn: DeployQA`
- `condition: succeeded()`
- Environment `PROD` tiene aprobación manual.

Pasos análogos a QA:

1. **API PROD**:
   - Imagen: `yagogandara/todos-api:$(Build.BuildId)`.
   - `APP_ENV=prod`.

2. **WEB PROD**:
   - Imagen: `yagogandara/todos-web:$(Build.BuildId)`.
   - `APP_ENV=prod`.
   - `API_BASE_URL=$(apiBaseUrlPROD)`.

3. **Smoke tests PROD** (opcional):
   - Poll a `readyz`, `healthz` y front.

---

## 7. Troubleshooting

- **Front 404 en QA/PROD (container)**:
  - Verificar que la imagen de frontend exponga correctamente `index.html`.
  - Revisar en Kudu/SSH que `site/wwwroot` contenga los archivos del build Angular.

- **API devuelve 500 en `/api/todos`**:
  - Confirmar `DB_URL=sqlite:////home/data/app.db`.
  - Revisar logs de la WebApp (Application Logs / Container Logs).
  - Confirmar que `/home/data` existe (en los containers se crea en el Dockerfile).

- **Seed no corre**:
  - Validar `SEED_TOKEN`.
  - Revisar que `SEED_ON_START=true` sólo en entornos donde se desea autoseed.

- **Cypress falla en CI**:
  - Revisar que el paso “Start backend API for Cypress” no haya fallado.
  - Ver logs de `uvicorn.log` en el agente.
  - Revisar que `environment.apiBaseUrl` apunte a `http://localhost:8080` en `environment.ts` (modo dev/CI).
