"""Localized labels for diarization diagnostics, following the system locale."""
from PyQt6.QtCore import QLocale

_TEXT = {
    "Check diarization": ("Comprobar diarización", "Comprobar diarización"),
    "Check diarization availability": ("Comprobar disponibilidad de diarización", "Comprobar disponibilidá de diarización"),
    "Cancel check": ("Cancelar comprobación", "Cancelar comprobación"),
    "Diarization not checked.": ("Diarización sin comprobar.", "Diarización ensin comprobar."),
    "Diarization check result": ("Resultado de la comprobación de diarización", "Resultáu de la comprobación de diarización"),
    "Diarization not checked for this token.": ("Diarización sin comprobar para este token.", "Diarización ensin comprobar pa esti token."),
    "Checking diarization…": ("Comprobando diarización…", "Comprobando diarización…"),
    "Check cancelled. The current network request will finish in the background.": ("Comprobación cancelada. La petición de red en curso terminará en segundo plano.", "Comprobación cancelada. La petición de rede en cursu terminará en segundu planu."),
    "Check timed out. Retry when the network is available.": ("La comprobación ha agotado el tiempo. Vuelve a intentarlo cuando haya conexión.", "La comprobación agotó'l tiempu. Vuelvi a intentalo cuando heba conexón."),
    "Save settings to use any token changes for transcription.": ("Guarda los ajustes para usar los cambios del token en las transcripciones.", "Guarda los axustes pa usar los cambios del token nes trescripciones."),
    "Open settings for diarization": ("Abrir ajustes de diarización", "Abrir axustes de diarización"),
    "Diarization warning": ("Aviso de diarización", "Avisu de diarización"),
    "available": ("Disponible", "Disponible"),
    "problem": ("Problema", "Problema"),
    "indeterminate": ("Indeterminado", "Indetermináu"),
    "Diarization was not performed: add a Hugging Face token in Settings > Transcription & speakers, then retry.": ("No se realizó la diarización: añade un token de Hugging Face en Ajustes > Transcripción y hablantes y vuelve a intentarlo.", "Nun se fizo la diarización: amiesta un token de Hugging Face n'Axustes > Trescripción y falantes y vuelvi a intentalo."),
    "Diarization was not performed: pyannote.audio is unavailable or incompatible. Check the installation, then retry.": ("No se realizó la diarización: pyannote.audio no está disponible o es incompatible. Revisa la instalación y vuelve a intentarlo.", "Nun se fizo la diarización: pyannote.audio nun ta disponible o ye incompatible. Revisa la instalación y vuelvi a intentalo."),
    "Diarization was not performed: authentication or model access was denied. Check your Hugging Face token and model access in Settings.": ("No se realizó la diarización: se denegó la autenticación o el acceso al modelo. Revisa el token y los permisos en Ajustes.", "Nun se fizo la diarización: denegóse l'autenticación o l'accesu al modelu. Revisa'l token y los permisos n'Axustes."),
    "Diarization was not performed: Hugging Face could not be reached. Check the connection and try again.": ("No se realizó la diarización: no se pudo conectar con Hugging Face. Revisa la conexión y vuelve a intentarlo.", "Nun se fizo la diarización: nun se pudo coneutar con Hugging Face. Revisa la conexón y vuelvi a intentalo."),
    "Diarization was not performed: the model could not be loaded or run. Check Settings > Transcription & speakers, then retry.": ("No se realizó la diarización: no se pudo cargar o ejecutar el modelo. Revisa Ajustes > Transcripción y hablantes y vuelve a intentarlo.", "Nun se fizo la diarización: nun se pudo cargar o executar el modelu. Revisa Axustes > Trescripción y falantes y vuelvi a intentalo."),
    "Account and model resource access verified. Download, audio inference and GPU were not tested.": ("Cuenta y acceso a los recursos del modelo comprobados. No se han comprobado la descarga, el audio ni la GPU.", "Cuenta y accesu a los recursos del modelu comprobaos. Nun se comprobaron la descarga, l'audiu nin la GPU."),
    "Account and pipeline access verified; model dependencies could not be identified. Inference was not tested.": ("Cuenta y acceso al modelo comprobados; no se pudieron identificar sus dependencias. No se ha probado la inferencia.", "Cuenta y accesu al modelu comprobaos; nun se pudieron identificar les dependencies. Nun se probó la inferencia."),
    "Could not contact Hugging Face. Check your connection and retry. Cached models may still work offline.": ("No se pudo conectar con Hugging Face. Revisa la conexión y vuelve a intentarlo. Los modelos en caché podrían funcionar sin conexión.", "Nun se pudo coneutar con Hugging Face. Revisa la conexón y vuelvi a intentalo. Los modelos na caché podríen funcionar ensin conexón."),
}


def diarization_text(text, locale_name=None):
    language = (locale_name or QLocale.system().name()).split("_", 1)[0].lower()
    index = {"es": 0, "ast": 1}.get(language)
    if index is None:
        return text
    if text in _TEXT:
        return _TEXT[text][index]
    prefix = "Diarization was not performed: the model could not be loaded or run. Check Settings > Transcription & speakers, then retry."
    if text.startswith(prefix):
        detail = text[len(prefix):].replace(" Detail: ", " Detalle: " if index == 0 else " Detalle: ", 1)
        return _TEXT[prefix][index] + detail
    if text.startswith("Access to ") and " was denied (HTTP " in text:
        resource, status = text[len("Access to "):].split(" was denied (HTTP ", 1)
        code = status.split(").", 1)[0]
        return (f"Se denegó el acceso a {resource} (HTTP {code}). Revisa el token y las condiciones de acceso en Hugging Face." if index == 0 else
                f"Denegóse l'accesu a {resource} (HTTP {code}). Revisa'l token y les condiciones d'accesu en Hugging Face.")
    if text.startswith("Hugging Face returned HTTP "):
        code = text.split("HTTP ", 1)[1].split(";", 1)[0]
        return (f"Hugging Face respondió HTTP {code}; vuelve a intentarlo más tarde. No se ha probado la inferencia." if index == 0 else
                f"Hugging Face respondió HTTP {code}; vuelvi a intentalo más tarde. Nun se probó la inferencia.")
    if text.startswith("Could not complete the check: "):
        return ("No se pudo completar la comprobación: " if index == 0 else "Nun se pudo completar la comprobación: ") + text.split(": ", 1)[1]
    return text
