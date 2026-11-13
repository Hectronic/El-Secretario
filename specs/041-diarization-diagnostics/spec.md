# SPEC-041: Diagnóstico y resultado de diarización

Status: Implemented — validación manual pendiente
Owner: `src/worker_components/`, `src/ui/settings/` y consumidores de transcripción directa y en cola
Last updated: 2026-11-12
Requests: REQ-041

## Funcionalidad actual (2026-11-12)

El botón **Check diarization** está disponible en Ajustes → Transcription & speakers. Comprueba explícitamente la importación local, la identidad de Hugging Face y el acceso a los recursos identificados en la configuración del modelo. No descarga pesos ni analiza audio. Informa alcance, fecha y resultados inciertos; el cambio de token invalida el resultado. El token editado debe guardarse para que la transcripción lo utilice.

Los resultados de transcripción directa y en cola registran el resultado efectivo y persisten una advertencia cuando falla la diarización. El panel de grabación la muestra y enlaza a los ajustes; el historial de cola muestra la advertencia durante la sesión. Si ya existe una transcripción, un resultado degradado no la sustituye. Se mantiene el flujo existente para reintentar y la política CUDA/CPU de SPEC-002/003.

La cancelación descarta el resultado y evita iniciar nuevas peticiones; la petición de red en curso termina en segundo plano, con timeout de 10 segundos por operación. La interfaz limita la espera a 45 segundos. El cierre invalida el trabajo pendiente; una importación nativa o resolución DNS fuera del control de Python puede tardar más. La comprobación de acceso no demuestra que la inferencia o GPU funcionen y no identifica de forma inequívoca todas las causas de un 403.

## Comportamiento anterior caracterizado

La diarización se solicita en la configuración de captura o transcripción y utiliza el token `hf_token` guardado en ajustes. El worker carga `pyannote/speaker-diarization-3.1`; intenta CUDA cuando corresponde y reintenta en CPU ante un fallo CUDA reconocido. El progreso se comunica con señales Qt. Hay flujos de transcripción directa y en cola.

Actualmente, si falta el token se omite la diarización; si falta pyannote se registra una advertencia y si falla la ejecución se registra la excepción. En los tres casos puede continuar la transcripción sin una advertencia duradera y el resultado establece `is_diarized` según la petición, no según el resultado. No hay evidencia suficiente para atribuir el problema concreto del usuario a una causa específica.

## Requisitos aprobados

REQ-041: hacer fácil averiguar por qué no funciona la diarización y qué hacer, y evitar que una transcripción sin diarizar se presente como diarizada. La propuesta fue aprobada por el usuario; su implementación y validación se detallan en el plan.

1. Añadir en Ajustes, junto al token de Hugging Face, una acción «Comprobar diarización» y un resultado legible: sin comprobar, comprobando, disponible, problema o resultado indeterminado. Mostrar fecha y alcance de la comprobación; invalidarla al cambiar el token. Las comprobaciones remotas se ejecutan solo a petición explícita, en segundo plano, con tiempo límite y sin bloquear la interfaz.
2. Verificar por etapas dependencia y compatibilidad local, presencia de token, autenticación y acceso efectivo a los recursos del modelo configurado y sus dependencias. No descargar modelos ni ejecutar inferencia larga como parte de la comprobación ligera. Identificar por separado lo comprobado y lo que sigue sin comprobar, incluso ante caché local o falta de red: una validación de acceso no garantiza que una inferencia real vaya a funcionar.
3. Presentar una causa y un siguiente paso cuando haya evidencia suficiente: token ausente o rechazado, acceso/permisos o condiciones pendientes para recursos concretos, conexión o servicio, dependencia ausente/incompatible, fallo del modelo o de ejecución. No afirmar que un token ha caducado ni que faltan condiciones cuando la respuesta solo permite concluir «autenticación o acceso denegados»; dar pasos para comprobar ambas posibilidades. Errores desconocidos incluyen diagnóstico genérico y detalle técnico saneado.
4. En transcripción directa y en cola, si se solicitó diarización y falla o se omite, conservar la transcripción lograda, mostrar una advertencia visible y persistente en el resultado o tarea con causa y acción, y mantener `is_diarized=false`. Si hubo diarización efectiva, guardar `true`; si no se solicitó, `false` sin advertencia. Los fallos recuperables no deben bloquear la cola siguiente. Distinguir ejecución satisfactoria de la cantidad de hablantes reconocidos; una grabación con una persona no demuestra un fallo.
5. Ofrecer desde el resultado o tarea una ruta clara para abrir ajustes y volver a comprobar/reintentar mediante el flujo existente. Al reintentar, no borrar ni sobrescribir la transcripción previa si el nuevo intento falla, se cancela o devuelve un resultado degradado. Cualquier sustitución sigue las reglas existentes de edición y persistencia y debe ser segura.
6. Evitar filtrar el token en mensajes, detalles, logs o pruebas. No leer ni enviar audio en la comprobación ligera. Respetar configuración de CPU/CUDA y el fallback existente, sin cargar modelos en la interfaz ni cambiar las preferencias del usuario.

## Criterios de aceptación

- Un token vacío produce una indicación y ruta a ajustes; un token rechazado se distingue de una ausencia de red solo cuando hay evidencia suficiente. Un 403 ambiguo no se etiqueta como token caducado.
- Un acceso válido a los recursos consultados muestra qué se ha validado; red no disponible produce estado indeterminado aunque puedan existir modelos cacheados. Cambiar el token invalida el resultado anterior y una respuesta antigua no lo sobrescribe.
- Una dependencia ausente/incompatible se identifica con una acción apropiada; errores inesperados no muestran secretos y conservan un mensaje útil.
- Una prueba en segundo plano mantiene operativa la UI, presenta tiempo límite y limpia sus recursos al cerrar o cancelar. La comprobación remota solo se ejecuta al pedirla.
- En éxito, fallo, omisión, fallback CUDA/CPU y cancelación se conserva la semántica correcta de estado y limpieza; en fallo de diarización se guarda el texto sin etiquetarlo como diarizado y el usuario puede descubrir la causa después de terminar el trabajo.
- La transcripción directa, la cola y el procesamiento por lotes aplican el mismo contrato; un fallo recuperable no impide procesar el siguiente elemento. Un reintento fallido no destruye el texto anterior.
- Los textos y acciones son accesibles, se adaptan a los idiomas admitidos por el proyecto y se documentan en los README que correspondan.

## Arquitectura y propiedad

- SPEC-003 mantiene el contrato de diarización y hablantes; esta spec define el diagnóstico y la comunicación del resultado; SPEC-003 se ha actualizado.
- `src/worker_components/`: comprobación y resultado tipado/saneado con estados y causas, conservando las señales y compatibilidad existentes. Recursos externos y autenticación encapsulados tras una frontera sustituible en tests; no duplicar la configuración del modelo.
- `src/ui/settings/`: controles y comprobación asíncrona; SPEC-037 mantiene la presentación de ajustes.
- `src/ui/recording/` y `src/app/summary_queue/` / `src/ui/summary_queue/`: comunicar advertencias y continuidad, respetando SPEC-011 y SPEC-017; `src/persistence/` es responsable del estado persistido cuando sea necesario. Revisar también el flujo de lotes y la transición de registros existentes, sin migrar datos históricos basándose en suposiciones.
- No introducir otro proveedor de diarización ni cambiar modelo o versiones por defecto en esta propuesta.

## Evidencia y limitaciones

Código actual: [transcriber_thread.py](../../src/worker_components/transcriber_thread.py), [runtime.py](../../src/worker_components/runtime.py), [transcription_flow.py](../../src/ui/recording/transcription_flow.py), [queue execution](../../src/app/summary_queue/execution.py) y [settings catalog](../../src/ui/settings/catalog.py). Cobertura: [diagnóstico](../../tests/worker_components/test_diarization_diagnostics.py), [integración Qt/SQLite](../../tests/integration/test_diarization_diagnostics.py), [worker](../../tests/worker/test_worker_integration.py) y [cola](../../tests/test_summary_task_queue_integration.py).

Los mensajes de diagnóstico y los avisos se muestran en español, asturiano o inglés según el idioma del sistema. La causa del fallo de la instalación del usuario es desconocida. El diagnóstico remoto estará sujeto a disponibilidad de red y a la información proporcionada por el servicio; las comprobaciones no prueban calidad, audio real ni disponibilidad de GPU. Validación, implementación y fechas se registran en [plan.md](plan.md).
