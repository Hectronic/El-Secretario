# Guía para Agentes AI

Este documento contiene información útil y normas estrictas para agentes de IA que trabajen en este repositorio.

## Normas Generales

1.  **Tests Obligatorios**:
    *   Siempre se debe verificar el código generado o modificado mediante tests.
    *   **Toda nueva funcionalidad debe incluir nuevos tests** (unitarios o de integración según corresponda).
    *   Nunca asumas que el código funciona sin probarlo.

2.  **Documentación Actualizada**:
    *   **La documentación debe mantenerse al día.**
    *   Con cada nueva funcionalidad o cambio significativo, verifica y actualiza la documentación pertinente (README, guías de instalación, comentarios en código, etc.).

3.  **Contexto del Proyecto**:
    *   Este proyecto utiliza un sistema de logs en `log/app.log`. Utilízalo para depurar.
    *   La estructura del proyecto separa el código fuente en `src/` y los tests en `tests/`.

## Flujo de Trabajo Recomendado

1.  Entender el requerimiento.
2.  Planificar los cambios (crear/modificar archivos).
3.  Implementar los cambios.
4.  **Crear/Actualizar Tests**.
5.  Ejecutar Tests y Verificar.
6.  Actualizar Documentación.
