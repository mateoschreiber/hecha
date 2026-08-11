# Despliegue y operación

Esta guía permite instalar `hecha` desde cero en Linux o Windows y operarlo en un VPS Linux. El stack no necesita ninguna clave de SILpy: todas las fuentes utilizadas son públicas.

## 1. Qué se instala

| Servicio | Responsabilidad | Accesible desde Internet |
|---|---|---|
| `proxy` | Caddy, única entrada HTTP | Sí, puerto 8080 local; 80/443 en VPS si se configura TLS |
| `web` | Next.js, interfaz y SSR | No |
| `api` | FastAPI, datos locales y cola de sincronización | No |
| `worker` | Sincroniza SILpy bajo demanda | No; tiene salida a Internet |
| `migrate` | Ejecuta Alembic y termina | No |
| `db` | PostgreSQL, fuente única de verdad | No |

La red `internal` está marcada como interna. El worker es el único servicio conectado también a la red `egress`, por la que consulta SILpy. El volumen Docker `postgres-data` conserva la base al reiniciar o recrear contenedores.

> PostgreSQL usa autenticación `trust` exclusivamente dentro de la red Docker interna. Nunca agregues un mapeo de puerto para `db`, `api` o `web`.

## 2. Requisitos

### Todos los equipos

- 4 GB de RAM disponibles para Docker (6 GB recomendados durante builds).
- 10 GB de disco libre para imágenes, base y respaldos.
- Acceso saliente a Docker Hub y `https://silpy.congreso.gov.py`.
- Git, si se clonará desde GitHub.

Comprobación:

```bash
docker --version
docker compose version
docker compose config --help
```

Se requiere Docker Compose v2, invocado como `docker compose` (con espacio).

### Linux

Instalá Docker Engine y el plugin oficial Docker Compose para tu distribución. Asegurá que el usuario pueda ejecutar Docker sin `sudo` o anteponé `sudo` a todos los comandos de esta guía.

```bash
docker run --rm hello-world
```

Si usás un firewall local, permití sólo el puerto 8080 para la instalación local.

### Windows 10/11

1. Instalá [Docker Desktop](https://www.docker.com/products/docker-desktop/) y habilitá el backend WSL 2 durante el asistente.
2. Abrí Docker Desktop y esperá a que indique que el motor está en ejecución.
3. Usá PowerShell 7 o Windows PowerShell. Git for Windows es suficiente para clonar por HTTPS; para SSH configurá una clave en GitHub.
4. Si usás WSL, cloná dentro del sistema de archivos Linux (por ejemplo `~/src/hecha`) para mejores tiempos de build; evitá trabajar en `/mnt/c/...` cuando sea posible.

Comprobación en PowerShell:

```powershell
docker run --rm hello-world
```

No se necesita instalar Node.js, npm, Python, PostgreSQL o Redis en Windows.

## 3. Instalación local limpia

### Linux/macOS/WSL

```bash
git clone git@github.com:mateoschreiber/hecha.git
cd hecha
cp .env.example .env
docker compose config --quiet
docker compose up --build -d
```

### Windows PowerShell

```powershell
git clone git@github.com:mateoschreiber/hecha.git
Set-Location hecha
Copy-Item .env.example .env
docker compose config --quiet
docker compose up --build -d
```

`migrate` termina con código 0 una vez aplicado el esquema; esto es esperado. Confirmá el estado:

```bash
docker compose ps
curl --fail http://localhost:8080/api/v1/health/ready
curl http://localhost:8080/api/v1/meta/freshness
```

En PowerShell reemplazá los dos últimos comandos por:

```powershell
Invoke-WebRequest http://localhost:8080/api/v1/health/ready | Select-Object -Expand Content
Invoke-WebRequest http://localhost:8080/api/v1/meta/freshness | Select-Object -Expand Content
```

Abrí `http://localhost:8080`. Una base nueva puede mostrarse vacía hasta completar una sincronización.

## 4. Sincronización inicial y actualización

1. En la portada, pulsá **Sincronizar datos públicos**.
2. El API crea una única solicitud global. Si existe una activa, se reutiliza; si hubo una reciente, aplica un cooldown.
3. El worker toma la solicitud, consulta el buscador JSF de SILpy, obtiene detalles públicos necesarios (autores y documentos) y confirma lotes en PostgreSQL.
4. La barra del portal o el endpoint de progreso muestran la fase y contadores.

También puede solicitarse desde una terminal; esto no expone SILpy al visitante:

```bash
curl -X POST http://localhost:8080/api/v1/sync
curl http://localhost:8080/api/v1/sync/progress
```

PowerShell:

```powershell
Invoke-WebRequest -Method POST http://localhost:8080/api/v1/sync | Select-Object -Expand Content
Invoke-WebRequest http://localhost:8080/api/v1/sync/progress | Select-Object -Expand Content
```

La primera carga puede tardar porque SILpy entrega la información por ventanas mensuales y una ficha adicional por expediente incompleto. No cierres Docker durante una carga si querés que termine antes; si se interrumpe, los lotes ya confirmados permanecen disponibles y una nueva solicitud sólo completa datos ausentes o modificados.

## 5. Operación cotidiana

| Acción | Linux/macOS/WSL | Windows PowerShell |
|---|---|---|
| Estado | `docker compose ps` | `docker compose ps` |
| Logs web | `docker compose logs -f web` | Igual |
| Logs API | `docker compose logs -f api` | Igual |
| Logs de sincronización | `docker compose logs -f worker` | Igual |
| Detener sin borrar datos | `docker compose stop` | Igual |
| Iniciar de nuevo | `docker compose start` | Igual |

No uses `docker compose down -v` para mantenimiento normal: elimina el volumen PostgreSQL y, con él, los datos locales. `docker compose down` sin `-v` conserva el volumen, aunque `stop` suele ser suficiente.

## 6. Actualización reproducible

Antes de actualizar, hacé un backup y verificá que pueda leerse. Luego:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
docker compose config --quiet
docker compose build
docker compose run --rm migrate
docker compose up -d --no-deps --force-recreate api worker web proxy
curl --fail http://localhost:8080/api/v1/health/ready
curl http://localhost:8080/api/v1/dashboard/summary
```

En Windows los mismos comandos funcionan en PowerShell; sustituí `curl` por `Invoke-WebRequest` si el alias de `curl` no se comporta como `curl.exe`.

La migración se ejecuta antes de recrear API, worker y web. Todos deben proceder del mismo commit. Si una imagen no construye, no recrees los servicios: corregí el error o volvé al commit anterior.

## 7. Backup y restauración

Creá el directorio local de respaldos si no existe. No se versiona en Git.

### Backup en Linux/macOS/WSL

```bash
mkdir -p backups
docker compose exec -T db pg_dump -U hecha -d hecha -Fc > backups/hecha.dump
docker compose exec -T db pg_restore -l /dev/stdin < backups/hecha.dump | head
```

El segundo comando comprueba que el dump es legible.

### Backup en Windows PowerShell

La copia se hace desde el contenedor para preservar correctamente el formato binario:

```powershell
New-Item -ItemType Directory -Force backups | Out-Null
docker compose exec -T db sh -lc "pg_dump -U hecha -d hecha -Fc -f /tmp/hecha.dump"
$db = docker compose ps -q db
docker cp "${db}:/tmp/hecha.dump" ".\backups\hecha.dump"
docker compose exec -T db pg_restore -l /tmp/hecha.dump | Select-Object -First 10
```

### Restauración

> **Atención:** restaurar reemplaza los datos actuales de la base. Detené los servicios de aplicación y asegurá que el backup corresponda al entorno objetivo.

Linux/macOS/WSL:

```bash
docker compose stop proxy web api worker
docker compose cp backups/hecha.dump db:/tmp/hecha.dump
docker compose exec -T db pg_restore -U hecha -d hecha --clean --if-exists /tmp/hecha.dump
docker compose start api worker web proxy
curl --fail http://localhost:8080/api/v1/health/ready
```

Windows PowerShell:

```powershell
docker compose stop proxy web api worker
$db = docker compose ps -q db
docker cp ".\backups\hecha.dump" "${db}:/tmp/hecha.dump"
docker compose exec -T db pg_restore -U hecha -d hecha --clean --if-exists /tmp/hecha.dump
docker compose start api worker web proxy
```

Si la restauración atraviesa migraciones antiguas, ejecutá `docker compose run --rm migrate` antes de iniciar API y worker.

## 8. Despliegue en VPS Linux

El alcance de este repositorio es un host Docker. Para exponer un dominio con TLS:

1. Creá un registro DNS `A`/`AAAA` hacia el VPS y confirmá su propagación.
2. Permití TCP 80 y 443 en el firewall del proveedor y del sistema operativo.
3. Cambiá `infra/caddy/Caddyfile` de `:80` al nombre de dominio, por ejemplo `datos.ejemplo.gov.py`.
4. En un override no versionado, publicá únicamente Caddy en 80 y 443:

```yaml
services:
  proxy:
    ports:
      - "80:80"
      - "443:443"
```

5. Copiá `.env.example` a `.env`, ejecutá la instalación local y verificá el dominio HTTPS.
6. Configurá backups externos cifrados del archivo de dump; el volumen local no es un backup.

No abras 5432, 8000 ni 3000. Caddy gestiona el certificado una vez que DNS y los puertos 80/443 son accesibles. El override de producción no debe añadir secretos al repositorio.

## 9. Diagnóstico

| Síntoma | Comprobación | Acción segura |
|---|---|---|
| Portal no abre | `docker compose ps`, `docker compose logs proxy` | Confirmá que 8080 no esté ocupado y reiniciá `proxy` |
| API responde 500 | `docker compose logs api` | Confirmá estado de `db`, después `docker compose restart api` |
| Sincronización no avanza | `docker compose logs -f worker` y `/api/v1/sync/progress` | Verificá salida HTTPS a SILpy; no borres datos locales |
| Datos antiguos | `/api/v1/meta/freshness` | Solicitá sincronización; el portal conserva el último dato válido |
| Migración falla | `docker compose run --rm migrate` | Restaurá un backup probado o volvé al commit anterior |
| Disco lleno | `docker system df` | Hacé backup y eliminá sólo imágenes no usadas; no elimines `postgres-data` |

## 10. Smoke tests de entrega

Después de una instalación o actualización, comprobá:

```bash
docker compose config --quiet
docker compose ps
curl --fail http://localhost:8080/api/v1/health/live
curl --fail http://localhost:8080/api/v1/health/ready
curl http://localhost:8080/api/v1/meta/freshness
curl http://localhost:8080/api/v1/dashboard/summary
curl http://localhost:8080/api/v1/expedients?limit=1
```

Si hay datos sincronizados, abrí una ficha de expediente y confirmá que autores y documentos se sirvan desde el dominio local. SILpy no debe aparecer en logs de API o web durante esa navegación.
