# Backup Y Restore

## Neon PostgreSQL

- Crear backup antes de migraciones.
- Guardar evidencia de hora, rama y commit.
- Restaurar en base temporal antes de reemplazar produccion.

## SQLite Local

Archivo por defecto:

```text
backend/agroescudo_dev.db
```

Backup:

```powershell
Copy-Item backend\agroescudo_dev.db backend\agroescudo_dev.backup.db
```

Restore:

```powershell
Copy-Item backend\agroescudo_dev.backup.db backend\agroescudo_dev.db
```

## Gateway

- Exportar cola antes de reflashear si es posible.
- No borrar `/queue.bin` salvo que las lecturas hayan sido aceptadas o duplicadas por backend.

