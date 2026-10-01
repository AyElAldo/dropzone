# DropZone

### by AyElAldo

**DropZone** es un servidor HTTP ligero y portátil, escrito en Python puro (sin dependencias externas), pensado como **herramienta auxiliar para pentesting y CTFs**: levanta en segundos un punto de transferencia de archivos accesible desde cualquier dispositivo en la misma red, vía navegador.

Permite **subir** archivos desde cualquier máquina/dispositivo de la red (arrastrando y soltando o seleccionando desde el navegador) y **descargar** los archivos recibidos desde una interfaz web con listado en vivo.

---

## Advertencia de seguridad — LEE ESTO ANTES DE USARLO

**DropZone NO es una herramienta de transferencia segura de propósito general.** Fue diseñada específicamente como utilidad auxiliar en engagements de pentesting, laboratorios y CTFs, bajo las siguientes premisas:

- **No usa cifrado.** Todo el tráfico viaja en **HTTP plano**, sin TLS/HTTPS. Cualquiera que pueda capturar tráfico en la red (sniffing, ARP spoofing, etc.) puede ver e interceptar los archivos transferidos.
- **No tiene whitelist/blacklist de tipos de archivo.** Acepta **cualquier archivo**, de cualquier extensión o contenido (ejecutables, scripts, binarios maliciosos, etc.), sin ningún tipo de validación, escaneo o restricción.
- **No tiene autenticación.** Cualquier persona que pueda alcanzar la IP y el puerto del servidor (`0.0.0.0`, escucha en todas las interfaces) puede subir y descargar archivos libremente. No hay usuarios, contraseñas ni tokens.
- **Expone el servicio a toda la red** en la que corre (escucha en `0.0.0.0`), no solo a `localhost`.
- **No limpia ni sanea el contenido de los archivos**, solo normaliza el nombre para evitar *path traversal* (`../../etc/passwd`, etc.). El contenido en sí no se inspecciona.

**Por lo tanto:**

- Úsalo **únicamente** en redes controladas, aisladas o de laboratorio (p. ej. una red interna de un engagement autorizado, una VM de pruebas, una red CTF).
- **No lo expongas a Internet** ni a redes no confiables.
- **No lo uses para transferir información sensible o de producción.**
- Verifica siempre que tienes **autorización explícita** para desplegar este tipo de servicios en la red/objetivo donde lo vayas a usar.

> **Descargo de responsabilidad:** este script se entrega "tal cual", con fines educativos y de apoyo en pruebas de seguridad autorizadas. **El uso de esta herramienta es responsabilidad exclusiva de quien la ejecuta.** El autor no se hace responsable del mal uso, daños, pérdida de datos, exposición de información o cualquier consecuencia derivada de su uso en contextos no autorizados o fuera del alcance de un pentest/CTF legítimo.

---

## Características

- Servidor HTTP autónomo basado en `http.server` de la librería estándar de Python — **sin instalar dependencias**.
- Interfaz web integrada (una sola página HTML embebida en el script) con estética tipo terminal/CLI: minimalista, sin animaciones ni efectos pesados, pensada para cargar rápido incluso en equipos o redes limitadas.
- Subida de archivos por *drag & drop* o selección manual, con **múltiples archivos** y barra de progreso individual.
- Listado de archivos recibidos en tiempo real (auto-refresh cada 5 segundos) con nombre, tamaño y fecha/hora.
- Descarga directa de cualquier archivo recibido desde el navegador.
- Carpeta de almacenamiento configurable (por defecto `./uploads/`).
- Puerto configurable (por defecto `8080`).
- Muestra automáticamente la IP local de la máquina para compartir la URL en la red.
- Banner de arranque personalizado con la firma del autor (`by AyElAldo`).

---

## Requisitos

- Python 3.6 o superior.
- No requiere ninguna librería externa (solo librería estándar: `cgi`, `html`, `json`, `mimetypes`, `os`, `sys`, `socket`, `http.server`, `pathlib`, `datetime`).

> Nota: el módulo `cgi` está marcado como obsoleto (*deprecated*) desde Python 3.11 y será removido en versiones futuras (ver [PEP 594](https://peps.python.org/pep-0594/)). El script sigue funcionando en versiones actuales de Python 3, pero puede dejar de hacerlo en futuras versiones del lenguaje.

---

## Instalación

No requiere instalación. Basta con tener Python 3 y el archivo `dropzone.py`:

```bash
git clone <url-del-repo>
cd dropzone
```

---

## Uso

### Sintaxis general

```bash
python3 dropzone.py [puerto] [directorio_de_guardado]
```

Ambos argumentos son opcionales y posicionales.

### Ejemplos

**1. Uso por defecto** (puerto `8080`, guarda en `./uploads/`):

```bash
python3 dropzone.py
```

**2. Especificando un puerto distinto:**

```bash
python3 dropzone.py 9090
```

**3. Especificando puerto y carpeta de destino:**

```bash
python3 dropzone.py 9090 /tmp/transferencias
```

Al iniciar, el script imprime un panel con la información de conexión:

```
  ╔══════════════════════════════════════╗
  ║         DropZone File Server         ║
  ║             by AyElAldo              ║
  ╠══════════════════════════════════════╣
  ║  Local:    http://localhost:8080     ║
  ║  Red:      http://192.168.1.50       ║
  ║  Guardado: C:\...\uploads            ║
  ╚══════════════════════════════════════╝
  (Ctrl+C para detener)
```

- **Local**: para acceder desde la misma máquina donde corre el servidor.
- **Red**: la IP que debes compartir con otros equipos de la misma red local para que puedan subir/descargar archivos desde su propio navegador.

Para **detener** el servidor, usa `Ctrl + C` en la terminal.

### Flujo de uso típico en un engagement

1. Levanta DropZone en la máquina atacante (o en el equipo que hará de "punto de intercambio"), dentro de la red del objetivo/laboratorio:
   ```bash
   python3 dropzone.py 8080 /tmp/dropzone
   ```
2. Comparte la URL de red (ej. `http://192.168.1.50:8080`) con el otro extremo (otra terminal, otra máquina comprometida, un dispositivo móvil, etc.).
3. Desde cualquier navegador en esa red, arrastra el archivo a subir sobre la zona de *drop*, o haz clic para seleccionarlo.
4. El archivo queda disponible de inmediato en el listado **// ARCHIVOS RECIBIDOS**, desde donde cualquiera en la red puede descargarlo con un clic.
5. Al terminar, **detén el servidor** (`Ctrl+C`) y, si es necesario, **borra la carpeta de uploads** para no dejar artefactos en el sistema.

---

## Endpoints de la API

Aunque está pensado para usarse vía navegador, el servidor expone endpoints HTTP simples que también se pueden usar con herramientas como `curl`:

| Método | Ruta                     | Descripción                                               |
|--------|--------------------------|------------------------------------------------------------|
| GET    | `/`                      | Página web principal (interfaz de subida/descarga).         |
| GET    | `/files`                 | Lista en JSON los archivos recibidos (`name`, `size`, `time`). |
| GET    | `/download/<nombre>`     | Descarga el archivo indicado desde el directorio de guardado. |
| POST   | `/upload`                | Sube uno o más archivos (`multipart/form-data`, campo `file`). |

**Ejemplo de subida con `curl`:**

```bash
curl -F "file=@/ruta/al/archivo.txt" http://192.168.1.50:8080/upload
```

**Ejemplo de descarga con `curl`:**

```bash
curl -O http://192.168.1.50:8080/download/archivo.txt
```

**Ejemplo de listado:**

```bash
curl http://192.168.1.50:8080/files
```

---

## Consideraciones técnicas

- El servidor escucha en `0.0.0.0`, es decir, en **todas las interfaces de red** de la máquina donde corre — no solo en `localhost`.
- Los nombres de archivo subidos se normalizan con `Path(nombre).name` tanto al guardar como al descargar, para mitigar ataques de *path traversal* (`../../`). Esta es la **única** medida de seguridad implementada; no sustituye cifrado, autenticación ni validación de contenido.
- Si se sube un archivo con el mismo nombre que uno ya existente, **se sobrescribe sin confirmación**.
- No hay límite de tamaño de archivo ni control de cuota de disco: un uso malicioso o descuidado puede llenar el almacenamiento disponible.

---

## Buenas prácticas al usarlo

- Despliega DropZone solo en la red/segmento donde realmente lo necesitas, y durante el tiempo mínimo indispensable.
- Si es posible, restringe el acceso a nivel de firewall/red al rango de IPs involucradas en la prueba.
- No dejes el servidor corriendo una vez terminada la tarea; detenlo y elimina los archivos transferidos si ya no son necesarios.
- No lo utilices como mecanismo permanente de intercambio de archivos ni en entornos productivos.

---

## Licencia / Responsabilidad

Este proyecto se proporciona sin garantías de ningún tipo. Es responsabilidad de quien lo use garantizar que su despliegue cuenta con la **autorización correspondiente** (contrato de pentest, alcance de CTF, red de laboratorio propia, etc.) y que se respetan las leyes y normativas aplicables. El autor no asume responsabilidad por el uso indebido de esta herramienta.
