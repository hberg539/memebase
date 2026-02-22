# TODOs

- [x] Upload endpoint (`POST /api/memes`) should catch `PermissionError` (and other OS errors) on `f.save()` and return a proper JSON error response instead of crashing with a 500
