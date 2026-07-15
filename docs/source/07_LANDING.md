# 07. Landing comercial

Estado del documento: BORRADOR CONTROLADO  
Fecha de auditoria: 2026-07-02  
Fuente principal: `landing/`

## Proposito

La landing es la cara comercial publica de AgroEscudo. Debe comunicar:

- Monitoreo postcosecha.
- Riesgo operativo.
- Evidencia tecnica.
- Alertas y reportes.
- Pilotos comerciales con acopiadores, silos, galpones y agroindustrias.

No debe prometer modulos no existentes como blockchain, marketplace, scoring financiero o seguros automatizados.

## Stack confirmado

| Componente | Estado | Evidencia |
|---|---|---|
| Next.js | CONFIRMADO EN CODIGO | `landing/package.json` |
| React | CONFIRMADO EN CODIGO | `landing/package.json` |
| Tailwind CSS | CONFIRMADO EN CODIGO | `landing/tailwind.config.ts` |

## Archivos principales

| Archivo/carpeta | Proposito |
|---|---|
| `landing/app/` | Paginas de la landing. |
| `landing/components/` | Componentes comerciales. |
| `landing/public/` | Assets publicos. |
| `landing/package.json` | Scripts y dependencias. |
| `landing/README.md` | Guia local si existe. |

## Comandos

```powershell
cd landing
npm install
npm run build
```

Estado: NO VERIFICADO EN ESTA FASE. Ejecutar antes de publicar.

## Coherencia comercial

La landing debe usar lenguaje sobrio:

- "Monitoreo IoT postcosecha"
- "Alertas operativas"
- "Bitacora y trazabilidad"
- "Reportes tecnicos"
- "Piloto comercial"

Evitar:

- "IA autonoma" si no esta verificada.
- "Certificacion automatica".
- "Seguro integrado".
- "Marketplace".
- "Blockchain".

## URLs externas

Estado: PENDIENTE.

Antes de publicar, verificar:

- Enlaces a dashboard.
- Enlaces a WhatsApp/contacto.
- Politica de privacidad si se recopilan leads.
- Dominio final.

## Riesgos

| Riesgo | Estado | Accion |
|---|---|---|
| Mensajes comerciales por encima del producto real | RIESGO | Mantener claims basados en funciones verificadas. |
| Enlaces rotos | PENDIENTE | Smoke test antes de deploy. |
| Formulario de contacto sin backend | PENDIENTE | Usar canal claro o integracion validada. |

