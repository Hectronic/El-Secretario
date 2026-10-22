# SPEC-040: Registro de peticiones y especificaciones vivas

Status: Implemented
Owner: Repository documentation and feature stewards
Last updated: 2026-10-22

## Petición y problema

El usuario pide un archivo con cada cosa solicitada, ordenada, y specs vivas con la funcionalidad realmente existente. El índice omitía 020–033 y mantenía 018/019 como planificadas aunque sus artefactos ya registraban la implementación.

## Contrato existente

- REQUESTS.md conserva las peticiones con ID estable, orden, origen, estado y enlace al contrato propietario. El historial recuperado se identifica como reconstrucción de specs, sin atribuir fechas ni citas no disponibles.
- CURRENT.md permite localizar las 39 áreas funcionales existentes con resumen concreto, código propietario, cobertura identificada y límites de validación. Este sistema documental es la spec 040.
- Los spec.md son contratos vivos: cambios de comportamiento actualizan su propietario en la misma PR. Las propuestas y objetivos no medidos se distinguen de la implementación existente.
- Los planes conservan decisiones y resultados reproducibles; las tareas registran el trabajo restante. Implementado y validado son dimensiones distintas.
- AGENTS.md y la constitución hacen obligatoria esta sincronización; la plantilla la incorpora para nuevas áreas.

## Criterios de aceptación

1. Cada directorio numerado aparece en el índice y tiene una petición vinculada.
2. Las áreas existentes tienen referencias a código y pruebas presentes en el repositorio.
3. Las peticiones de esta sesión se conservan sin sustituir la petición original de revisar/publicar 039.
4. Los pendientes manuales de 038 y los límites de rendimiento siguen visibles.
5. Los tres README enlazan el mismo registro y catálogo.

## Propiedad y límites

Propietarios: specs/, AGENTS.md y .specify/memory/constitution.md. No modifica la ejecución de la aplicación. No reconstruye conversaciones a las que no se tiene acceso ni certifica todas las plataformas por pasar pruebas offscreen.

## Validación

Cobertura permanente en `tests/test_spec_registry.py`: enlaces locales, IDs y cobertura del inventario con el Python del venv; revisión del índice frente a los 40 directorios. No cruza un límite de ejecución de componentes; no requiere una prueba de integración adicional. La entrega conjunta de 039 sí requiere su cobertura SQLite/Qt y suite completa.
