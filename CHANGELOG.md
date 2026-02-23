# Changelog

## [0.3.0](https://github.com/hberg539/memebase/compare/v0.2.0...v0.3.0) (2026-02-23)


### Features

* **ui:** add rainbow gradient favicon with build script ([949b34b](https://github.com/hberg539/memebase/commit/949b34b547c68785372c60ad712fbf8cffc57411))


### Bug Fixes

* **config:** use local build instead of remote image in docker-compose ([28ca6e9](https://github.com/hberg539/memebase/commit/28ca6e9a9a5bbff46342540c2b726ff285e8dc59))
* **grid:** truncate long meme filenames with ellipsis while preserving extension ([bd268f0](https://github.com/hberg539/memebase/commit/bd268f0e8afb97767137e4cce40ac1e14c323359))
* **security:** validate URL scheme in upload-from-url endpoint ([299987c](https://github.com/hberg539/memebase/commit/299987c9d1ecd7caac44c2d2f0bbd348dbe53b5e))


### Refactoring

* extract service layer, split ai.py, deduplicate upload logic ([b4f1720](https://github.com/hberg539/memebase/commit/b4f17200899e7727258091689f62c2f890f1419f))


### Documentation

* add links to README badges ([5d42b0c](https://github.com/hberg539/memebase/commit/5d42b0ca116ff2f7734bac4e3aec29b423077dcb))
* add test status badge to README ([67f8a07](https://github.com/hberg539/memebase/commit/67f8a07100512fc693f6ab35622d0eee0473ab7a))
* update AGENTS.md with service layer, new tests, and CI info ([51ceaa6](https://github.com/hberg539/memebase/commit/51ceaa6d75c2d9b629dc31ed5f470a86e8f6d440))


### Styling

* add type hints to all Python source functions ([cade51a](https://github.com/hberg539/memebase/commit/cade51ac2feb6b057095ca48f514645e761909c1))


### Build System

* sync uv.lock version via release-please extra-files ([08685f6](https://github.com/hberg539/memebase/commit/08685f6593a7704887becc9fc0130d85afd4ecbb))


### CI/CD

* add pytest workflow for every push and PR ([5b6b6c0](https://github.com/hberg539/memebase/commit/5b6b6c0918cf271f56d8a4a666c15bed92b75b33))
* test on Python 3.10 and 3.14 ([2e69b9a](https://github.com/hberg539/memebase/commit/2e69b9af207bfeb937dc01d32d04b86b8c8ce538))


### Miscellaneous

* remove TODOS.md ([c3ac1ec](https://github.com/hberg539/memebase/commit/c3ac1ece3543f0910f0dd57c58f7fdb9a068ecd0))

## [0.2.0](https://github.com/hberg539/memebase/compare/v0.1.0...v0.2.0) (2026-02-23)


### Features

* initial memebase implementation ([e086855](https://github.com/hberg539/memebase/commit/e0868552346dbd21f1b7da95e0c709ba75568dfe))
