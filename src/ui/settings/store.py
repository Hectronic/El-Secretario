"""Small staged overlay over QSettings used by the Settings form adapters."""


class SettingsOverlay:
    """Let legacy panel ``save`` methods stage values without persisting them."""

    def __init__(self, source):
        self.source = source
        self._values = {}

    def value(self, key, defaultValue=None, type=None):
        value = self._values.get(key, self.source.value(key, defaultValue))
        if type is not None and value is not None:
            try:
                return type(value)
            except (TypeError, ValueError):
                return defaultValue
        return value

    def setValue(self, key, value):
        self._values[key] = value

    def contains(self, key):
        return key in self._values or self.source.contains(key)

    def allKeys(self):
        return sorted(set(self.source.allKeys()) | set(self._values))

    def childKeys(self):
        return [key for key in self.allKeys() if "/" not in key]

    def childGroups(self):
        groups = {key.split("/", 1)[0] for key in self.allKeys() if "/" in key}
        return sorted(groups)

    def remove(self, key):
        self._values[key] = _Removed

    def sync(self):
        """Match the QSettings surface without flushing staged edits."""

    def clear(self):
        self._values.clear()

    def changes(self, defaults=None):
        defaults = defaults or {}
        changed = {}
        for key, value in self._values.items():
            if value is _Removed:
                continue
            previous = self.source.value(key, defaults.get(key))
            if previous != value:
                changed[key] = value
        return changed

    def discard(self, keys):
        for key in keys:
            self._values.pop(key, None)


def clear_pending_restart_status(settings):
    """Mark restart-required settings active once the application starts again."""
    for key in (
        "settings/pending_restart_keys",
        "settings/pending_restart_values",
        "settings/pending_restart_pid",
    ):
        settings.remove(key)
    settings.sync()


class _RemovedType:
    pass


_Removed = _RemovedType()
